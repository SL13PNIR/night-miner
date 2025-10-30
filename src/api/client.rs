use anyhow::{Context, Result};
use reqwest::Client;
use tracing::{debug, info};

use super::models::*;

const BASE_URL: &str = "https://scavenger.prod.gd.midnighttge.io";

/// API client for the Scavenger Mine service
pub struct ScavengerClient {
    client: Client,
    base_url: String,
}

impl ScavengerClient {
    /// Create a new API client
    pub fn new() -> Result<Self> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(60))
            .user_agent("night-miner/1.0")
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self {
            client,
            base_url: BASE_URL.to_string(),
        })
    }

    /// Create a new API client with a custom base URL (useful for testing)
    #[allow(dead_code)]
    pub fn with_base_url(base_url: String) -> Result<Self> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .user_agent("night-miner/1.0")
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self { client, base_url })
    }

    /// GET /TandC - Obtain the Token End User Agreement
    pub async fn get_terms_and_conditions(
        &self,
        version: Option<&str>,
    ) -> Result<TermsAndConditions> {
        let url = if let Some(v) = version {
            format!("{}/TandC/{}", self.base_url, v)
        } else {
            format!("{}/TandC", self.base_url)
        };

        debug!("Fetching T&C from: {}", url);

        let response = self.client.get(&url).send().await?;

        if response.status().is_success() {
            let tandc = response.json::<TermsAndConditions>().await?;
            info!("Successfully fetched T&C version {}", tandc.version);
            Ok(tandc)
        } else {
            let error = response.json::<ApiError>().await?;
            anyhow::bail!("API error: {} - {}", error.error, error.message);
        }
    }

    /// POST /register - Register a Destination address to participate
    pub async fn register(
        &self,
        address: &str,
        signature: &str,
        pubkey: &str,
    ) -> Result<RegistrationResponse> {
        let url = format!(
            "{}/register/{}/{}/{}",
            self.base_url, address, signature, pubkey
        );

        debug!("Registering address: {}", address);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({}))
            .send()
            .await?;

        if response.status().is_success() {
            let reg_response = response.json::<RegistrationResponse>().await?;
            info!("Successfully registered address: {}", address);
            Ok(reg_response)
        } else {
            let error_text = response.text().await?;
            anyhow::bail!("Registration failed: {}", error_text);
        }
    }

    /// GET /challenge - Fetch the next available challenge
    pub async fn get_challenge(&self) -> Result<ChallengeResponse> {
        let url = format!("{}/challenge", self.base_url);

        debug!("Fetching current challenge");

        let response = self.client.get(&url).send().await?;

        if response.status().is_success() {
            let challenge = response.json::<ChallengeResponse>().await?;

            match &challenge.data {
                ChallengeData::Active { challenge, .. } => {
                    info!(
                        "Fetched challenge: {} (Day {}, Challenge {})",
                        challenge.challenge_id, challenge.day, challenge.challenge_number
                    );
                }
                ChallengeData::Before { starts_at } => {
                    info!("Mining hasn't started yet. Starts at: {}", starts_at);
                }
                ChallengeData::After => {
                    info!("Mining period has ended");
                }
            }

            Ok(challenge)
        } else {
            let error_text = response.text().await?;
            anyhow::bail!("Failed to fetch challenge: {}", error_text);
        }
    }

    /// POST /solution - Submit a solution to a challenge
    pub async fn submit_solution(
        &self,
        address: &str,
        challenge_id: &str,
        nonce: &str,
    ) -> Result<SolutionResponse> {
        let url = format!(
            "{}/solution/{}/{}/{}",
            self.base_url, address, challenge_id, nonce
        );

        debug!("Submitting solution for challenge: {}", challenge_id);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({}))
            .send()
            .await?;

        if response.status().is_success() {
            let solution = response.json::<SolutionResponse>().await?;
            info!("Solution accepted for challenge: {}", challenge_id);
            Ok(solution)
        } else {
            let error_text = response.text().await?;
            anyhow::bail!("Solution submission failed: {}", error_text);
        }
    }

    /// POST /donate_to - Re-assign solutions from one address to another
    pub async fn donate_to(
        &self,
        destination_address: &str,
        original_address: &str,
        signature: &str,
    ) -> Result<DonationResponse> {
        let url = format!(
            "{}/donate_to/{}/{}/{}",
            self.base_url, destination_address, original_address, signature
        );

        debug!(
            "Donating from {} to {}",
            original_address, destination_address
        );

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({}))
            .send()
            .await?;

        if response.status().is_success() {
            let donation = response.json::<DonationResponse>().await?;
            info!(
                "Successfully donated {} solutions from {} to {}",
                donation.solutions_consolidated, original_address, destination_address
            );
            Ok(donation)
        } else {
            let error_text = response.text().await?;
            anyhow::bail!("Donation failed: {}", error_text);
        }
    }

    /// GET /work_to_star_rate - Get daily STAR allocation rates
    pub async fn get_work_to_star_rate(&self) -> Result<WorkToStarRate> {
        let url = format!("{}/work_to_star_rate", self.base_url);

        debug!("Fetching work to star rate");

        let response = self.client.get(&url).send().await?;

        if response.status().is_success() {
            let rates = response.json::<WorkToStarRate>().await?;
            info!("Fetched {} days of STAR rates", rates.len());
            Ok(rates)
        } else {
            let error_text = response.text().await?;
            anyhow::bail!("Failed to fetch star rates: {}", error_text);
        }
    }
}

impl Default for ScavengerClient {
    fn default() -> Self {
        Self::new().expect("Failed to create default ScavengerClient")
    }
}
