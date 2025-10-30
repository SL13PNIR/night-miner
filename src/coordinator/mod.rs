use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, error, info, warn};

use crate::api::{ChallengeData, ScavengerClient};
use crate::miner::{MiningEngine, MiningResult};
use crate::wallet::WalletConfig;

/// Statistics about mining performance
#[derive(Debug, Default)]
pub struct MiningStats {
    pub challenges_attempted: u32,
    pub solutions_found: u32,
    pub solutions_submitted: u32,
    pub total_star_earned: u64,
}

impl MiningStats {
    pub fn report(&self) {
        info!("=== Mining Statistics ===");
        info!("Challenges attempted: {}", self.challenges_attempted);
        info!("Solutions found: {}", self.solutions_found);
        info!("Solutions submitted: {}", self.solutions_submitted);
        info!(
            "Success rate: {:.2}%",
            if self.challenges_attempted > 0 {
                (self.solutions_found as f64 / self.challenges_attempted as f64) * 100.0
            } else {
                0.0
            }
        );
        info!(
            "Total STAR earned: {} ({:.6} NIGHT)",
            self.total_star_earned,
            self.total_star_earned as f64 / 1_000_000.0
        );
    }
}

/// Coordinates the mining process - fetches challenges, mines, and submits solutions
pub struct MiningCoordinator {
    client: ScavengerClient,
    wallet: WalletConfig,
    mining_engine: MiningEngine,
    stats: MiningStats,
    challenge_timeout: Duration,
}

impl MiningCoordinator {
    /// Create a new mining coordinator
    pub fn new(
        wallet: WalletConfig,
        num_threads: Option<usize>,
        challenge_timeout_minutes: Option<u64>,
    ) -> Result<Self> {
        let client = ScavengerClient::new()?;
        let mining_engine = MiningEngine::new(num_threads).with_progress_bar(true);
        let challenge_timeout = Duration::from_secs(challenge_timeout_minutes.unwrap_or(55) * 60);

        Ok(Self {
            client,
            wallet,
            mining_engine,
            stats: MiningStats::default(),
            challenge_timeout,
        })
    }

    /// Run the mining coordinator indefinitely
    pub async fn run(&mut self) -> Result<()> {
        info!(
            "Starting mining coordinator for address: {}",
            self.wallet.get_address()
        );

        loop {
            match self.run_cycle().await {
                Ok(should_continue) => {
                    if !should_continue {
                        info!("Mining period has ended");
                        break;
                    }
                }
                Err(e) => {
                    error!("Error in mining cycle: {:#}", e);
                    // Wait a bit before retrying
                    sleep(Duration::from_secs(30)).await;
                }
            }
        }

        self.stats.report();
        Ok(())
    }

    /// Run a single mining cycle (fetch challenge, mine, submit)
    /// Returns Ok(true) if mining should continue, Ok(false) if mining period ended
    async fn run_cycle(&mut self) -> Result<bool> {
        // Fetch current challenge
        let challenge_response = self.client.get_challenge().await?;

        match challenge_response.data {
            ChallengeData::Before { starts_at } => {
                info!("Mining hasn't started yet. Starts at: {}", starts_at);
                let wait_time = calculate_wait_time(starts_at);
                info!(
                    "Waiting {} seconds until mining starts...",
                    wait_time.as_secs()
                );
                sleep(wait_time).await;
                return Ok(true);
            }
            ChallengeData::After => {
                info!("Mining period has ended");
                return Ok(false);
            }
            ChallengeData::Active {
                challenge,
                next_challenge_starts_at,
                current_day,
                max_day,
                ..
            } => {
                let difficulty_level = crate::miner::difficulty_to_level(&challenge.difficulty);
                info!(
                    "Day {}/{} - Challenge {} - Difficulty: {} ({})",
                    current_day, max_day, challenge.challenge_id, challenge.difficulty, difficulty_level
                );

                // Debug: Print full challenge details
                debug!("Challenge details:");
                debug!("  challenge_id: {}", challenge.challenge_id);
                debug!("  difficulty: {}", challenge.difficulty);
                debug!("  no_pre_mine: {}", challenge.no_pre_mine);
                debug!("  no_pre_mine_hour: {}", challenge.no_pre_mine_hour);
                debug!("  latest_submission: {}", challenge.latest_submission);

                // Initialize ROM for this challenge
                self.mining_engine
                    .initialize_rom(&challenge.no_pre_mine)
                    .context("Failed to initialize ROM")?;

                // Mine for a solution
                self.stats.challenges_attempted += 1;

                let mining_result = self.mining_engine.mine(
                    &challenge,
                    self.wallet.get_address(),
                    Some(self.challenge_timeout),
                )?;

                match mining_result {
                    MiningResult::Solution(nonce) => {
                        self.stats.solutions_found += 1;

                        // Submit the solution - lowercase per API spec
                        let nonce_hex = format!("{:016x}", nonce);
                        match self
                            .client
                            .submit_solution(
                                self.wallet.get_address(),
                                &challenge.challenge_id,
                                &nonce_hex,
                            )
                            .await
                        {
                            Ok(response) => {
                                info!(
                                    "Solution submitted successfully! Receipt timestamp: {}",
                                    response.crypto_receipt.timestamp
                                );
                                self.stats.solutions_submitted += 1;

                                // Try to fetch star rates to estimate earnings
                                if let Ok(star_rates) = self.client.get_work_to_star_rate().await {
                                    if let Some(rate) = star_rates.get((current_day - 1) as usize) {
                                        self.stats.total_star_earned += rate;
                                        info!(
                                            "Earned {} STAR ({:.6} NIGHT) for this solution",
                                            rate,
                                            *rate as f64 / 1_000_000.0
                                        );
                                    }
                                }
                            }
                            Err(e) => {
                                error!("Failed to submit solution: {:#}", e);
                            }
                        }
                    }
                    MiningResult::Timeout => {
                        warn!("Mining timed out for challenge {}", challenge.challenge_id);
                    }
                    MiningResult::Stopped => {
                        warn!("Mining was stopped");
                    }
                }

                // Wait until next challenge
                let wait_time = calculate_wait_time(next_challenge_starts_at);
                if wait_time.as_secs() > 0 {
                    info!(
                        "Waiting {} seconds until next challenge...",
                        wait_time.as_secs()
                    );
                    sleep(wait_time).await;
                }

                return Ok(true);
            }
        }
    }

    /// Get current statistics
    #[allow(dead_code)]
    pub fn get_stats(&self) -> &MiningStats {
        &self.stats
    }
}

/// Calculate how long to wait until a given time
fn calculate_wait_time(target: DateTime<Utc>) -> Duration {
    let now = Utc::now();
    let diff = target.signed_duration_since(now);

    if diff.num_seconds() > 0 {
        Duration::from_secs(diff.num_seconds() as u64)
    } else {
        Duration::from_secs(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration as ChronoDuration;

    #[test]
    fn test_calculate_wait_time_future() {
        let future = Utc::now() + ChronoDuration::seconds(3600);
        let wait = calculate_wait_time(future);
        assert!(wait.as_secs() > 3500 && wait.as_secs() <= 3600);
    }

    #[test]
    fn test_calculate_wait_time_past() {
        let past = Utc::now() - ChronoDuration::seconds(3600);
        let wait = calculate_wait_time(past);
        assert_eq!(wait.as_secs(), 0);
    }
}
