use anyhow::{Context, Result};
use ashmaize::{hash, Rom, RomGenerationType};
use crossbeam::channel::{bounded, Sender};
use indicatif::{ProgressBar, ProgressStyle};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};
use tracing::{debug, info, warn};

use crate::api::Challenge;

const ASHMAIZE_NB_LOOPS: u32 = 8;
const ASHMAIZE_NB_INSTRS: u32 = 256;
const ASHMAIZE_PRE_SIZE: usize = 16 * 1024 * 1024; // 16 MB
const ASHMAIZE_MIXING_NUMBERS: usize = 4;
const ASHMAIZE_ROM_SIZE: usize = 1024 * 1024 * 1024; // 1 GB

/// Result of mining operation
#[derive(Debug, Clone)]
pub enum MiningResult {
    /// Solution found with the given nonce
    Solution(u64),
    /// Mining was stopped before finding a solution
    Stopped,
    /// Timeout reached before finding a solution
    Timeout,
}

/// Mining engine that searches for valid nonces
pub struct MiningEngine {
    rom: Arc<Rom>,
    num_threads: usize,
    progress_bar: Option<ProgressBar>,
}

impl MiningEngine {
    /// Create a new mining engine with the given number of threads
    pub fn new(num_threads: Option<usize>) -> Self {
        let num_threads = num_threads.unwrap_or_else(num_cpus::get);
        info!("Initializing mining engine with {} threads", num_threads);

        Self {
            rom: Arc::new(Rom::new(
                b"", // Will be re-initialized per challenge
                RomGenerationType::TwoStep {
                    pre_size: ASHMAIZE_PRE_SIZE,
                    mixing_numbers: ASHMAIZE_MIXING_NUMBERS,
                },
                ASHMAIZE_ROM_SIZE,
            )),
            num_threads,
            progress_bar: None,
        }
    }

    /// Initialize the ROM with the challenge's no_pre_mine value
    pub fn initialize_rom(&mut self, no_pre_mine: &str) -> Result<()> {
        info!("Initializing ROM with no_pre_mine: {}", no_pre_mine);

        // CRITICAL: Use the hex string bytes directly as the key, NOT decoded bytes!
        // The website does: builder.key(new TextEncoder().encode(no_pre_mine))
        // which encodes the HEX STRING ITSELF (e.g., "d201ad52...") as UTF-8 bytes
        // NOT the decoded binary representation!
        let seed = no_pre_mine.as_bytes();

        let start = Instant::now();
        self.rom = Arc::new(Rom::new(
            seed,
            RomGenerationType::TwoStep {
                pre_size: ASHMAIZE_PRE_SIZE,
                mixing_numbers: ASHMAIZE_MIXING_NUMBERS,
            },
            ASHMAIZE_ROM_SIZE,
        ));

        let elapsed = start.elapsed();
        info!("ROM initialized in {:.2}s", elapsed.as_secs_f64());

        Ok(())
    }

    /// Enable progress bar for visual feedback
    pub fn with_progress_bar(mut self, enabled: bool) -> Self {
        if enabled {
            let pb = ProgressBar::new_spinner();
            pb.set_style(
                ProgressStyle::default_spinner()
                    .template("{spinner:.green} [{elapsed_precise}] {msg} {per_sec}")
                    .unwrap()
                    .progress_chars("#>-"),
            );
            self.progress_bar = Some(pb);
        }
        self
    }

    /// Mine for a solution to the given challenge
    ///
    /// This will search for a nonce that produces a hash meeting the difficulty requirement
    pub fn mine(
        &self,
        challenge: &Challenge,
        address: &str,
        timeout: Option<Duration>,
    ) -> Result<MiningResult> {
        let difficulty_level = difficulty_to_level(&challenge.difficulty);
        info!(
            "Starting mining for challenge {} with difficulty {} ({})",
            challenge.challenge_id, challenge.difficulty, difficulty_level
        );

        let difficulty_mask = parse_difficulty(&challenge.difficulty)?;
        let start_time = Instant::now();

        // Shared state
        let found = Arc::new(AtomicBool::new(false));
        let solution_nonce = Arc::new(AtomicU64::new(0));
        let hash_count = Arc::new(AtomicU64::new(0));

        // Channel for communication
        let (tx, rx) = bounded(self.num_threads * 2);

        // Spawn worker threads
        let mut handles = Vec::new();
        for thread_id in 0..self.num_threads {
            let rom = Arc::clone(&self.rom);
            let found = Arc::clone(&found);
            let solution_nonce = Arc::clone(&solution_nonce);
            let hash_count = Arc::clone(&hash_count);
            let tx = tx.clone();

            let challenge = challenge.clone();
            let address = address.to_string();

            handles.push(thread::spawn(move || {
                mine_worker(
                    thread_id,
                    rom,
                    &challenge,
                    &address,
                    difficulty_mask,
                    found,
                    solution_nonce,
                    hash_count,
                    tx,
                );
            }));
        }

        // Drop the original sender so the channel can close
        drop(tx);

        // Monitor progress
        let monitor_handle = if let Some(pb) = &self.progress_bar {
            let pb = pb.clone();
            let hash_count = Arc::clone(&hash_count);
            let found = Arc::clone(&found);

            Some(thread::spawn(move || {
                let mut last_count = 0u64;
                let mut last_time = Instant::now();

                while !found.load(Ordering::Relaxed) {
                    thread::sleep(Duration::from_millis(500));

                    let current_count = hash_count.load(Ordering::Relaxed);
                    let current_time = Instant::now();
                    let elapsed = current_time.duration_since(last_time).as_secs_f64();

                    if elapsed > 0.0 {
                        let hash_rate = (current_count - last_count) as f64 / elapsed;
                        pb.set_message(format!(
                            "Hashes: {} | Rate: {:.2} H/s",
                            current_count, hash_rate
                        ));
                    }

                    last_count = current_count;
                    last_time = current_time;
                }

                pb.finish_with_message(format!(
                    "Mining completed. Total hashes: {}",
                    hash_count.load(Ordering::Relaxed)
                ));
            }))
        } else {
            None
        };

        // Wait for result or timeout
        let result = if let Some(timeout_duration) = timeout {
            match rx.recv_timeout(timeout_duration) {
                Ok(nonce) => MiningResult::Solution(nonce),
                Err(_) => {
                    found.store(true, Ordering::Relaxed);
                    MiningResult::Timeout
                }
            }
        } else {
            match rx.recv() {
                Ok(nonce) => MiningResult::Solution(nonce),
                Err(_) => MiningResult::Stopped,
            }
        };

        // Signal threads to stop
        found.store(true, Ordering::Relaxed);

        // Wait for all threads to complete
        for handle in handles {
            let _ = handle.join();
        }

        if let Some(handle) = monitor_handle {
            let _ = handle.join();
        }

        let elapsed = start_time.elapsed();
        let total_hashes = hash_count.load(Ordering::Relaxed);
        let hash_rate = total_hashes as f64 / elapsed.as_secs_f64();

        match result {
            MiningResult::Solution(nonce) => {
                info!(
                    "Solution found! Nonce: {:016x} | Time: {:.2}s | Total hashes: {} | Rate: {:.2} H/s",
                    nonce, elapsed.as_secs_f64(), total_hashes, hash_rate
                );
            }
            MiningResult::Timeout => {
                warn!(
                    "Mining timeout after {:.2}s | Total hashes: {} | Rate: {:.2} H/s",
                    elapsed.as_secs_f64(),
                    total_hashes,
                    hash_rate
                );
            }
            MiningResult::Stopped => {
                warn!("Mining stopped");
            }
        }

        Ok(result)
    }
}

/// Worker thread function
fn mine_worker(
    thread_id: usize,
    rom: Arc<Rom>,
    challenge: &Challenge,
    address: &str,
    difficulty_mask: [u8; 4],
    found: Arc<AtomicBool>,
    solution_nonce: Arc<AtomicU64>,
    hash_count: Arc<AtomicU64>,
    tx: Sender<u64>,
) {
    debug!("Worker thread {} started", thread_id);

    // Each thread starts at random position and increments
    use std::time::{SystemTime, UNIX_EPOCH};
    let random_offset = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis() as u64;
    let nonce_start = ((thread_id as u64) << 56) | (random_offset & 0x00FFFFFFFFFFFFFF);
    
    let mut nonce = nonce_start;
    let mut local_hash_count = 0u64;

    while !found.load(Ordering::Relaxed) {
        
        // Construct preimage
        let preimage = construct_preimage(nonce, address, challenge);

        // Hash with AshMaize
        let hash_result = hash(&preimage, &rom, ASHMAIZE_NB_LOOPS, ASHMAIZE_NB_INSTRS);

        local_hash_count += 1;

        // Check if hash meets difficulty
        if check_difficulty(&hash_result, &difficulty_mask) {
            debug!(
                "Thread {} found solution! Nonce: {:016x}",
                thread_id, nonce
            );
            
            found.store(true, Ordering::Relaxed);
            solution_nonce.store(nonce, Ordering::Relaxed);
            let _ = tx.send(nonce);
            break;
        }

        // Update global hash count periodically
        if local_hash_count % 1000 == 0 {
            hash_count.fetch_add(1000, Ordering::Relaxed);
            local_hash_count = 0;
        }
        
        nonce = nonce.wrapping_add(1);
    }

    // Update final hash count
    if local_hash_count > 0 {
        hash_count.fetch_add(local_hash_count, Ordering::Relaxed);
    }

    debug!("Worker thread {} stopped", thread_id);
}

/// Construct the preimage for hashing according to the specification
fn construct_preimage(nonce: u64, address: &str, challenge: &Challenge) -> Vec<u8> {
    let mut preimage = Vec::new();

    // 1. nonce (16 hex chars = 8 bytes) - LOWERCASE hex string per working examples
    let nonce_str = format!("{:016x}", nonce);
    preimage.extend_from_slice(nonce_str.as_bytes());

    // 2. address
    preimage.extend_from_slice(address.as_bytes());

    // 3. challenge_id
    preimage.extend_from_slice(challenge.challenge_id.as_bytes());

    // 4. difficulty (hex string, not decoded)
    preimage.extend_from_slice(challenge.difficulty.as_bytes());

    // 5. no_pre_mine (hex string, not decoded)
    preimage.extend_from_slice(challenge.no_pre_mine.as_bytes());

    // 6. latest_submission
    preimage.extend_from_slice(challenge.latest_submission.as_bytes());

    // 7. no_pre_mine_hour
    preimage.extend_from_slice(challenge.no_pre_mine_hour.as_bytes());

    // Debug: log the preimage for comparison with working solution
    tracing::debug!(
        "Preimage constructed: {}",
        String::from_utf8_lossy(&preimage)
    );
    tracing::debug!("Nonce: {} | Address: {} | Challenge: {} | Difficulty: {} | NoPreMine: {} | Timestamp: {} | Hour: {}",
        nonce_str, address, challenge.challenge_id, challenge.difficulty, challenge.no_pre_mine,
        challenge.latest_submission, challenge.no_pre_mine_hour);

    preimage
}

/// Parse difficulty hex string into byte mask
fn parse_difficulty(difficulty: &str) -> Result<[u8; 4]> {
    let bytes = hex::decode(difficulty).context("Failed to decode difficulty hex")?;

    if bytes.len() != 4 {
        anyhow::bail!("Difficulty must be exactly 4 bytes");
    }

    let mut mask = [0u8; 4];
    mask.copy_from_slice(&bytes);
    Ok(mask)
}

/// Check if hash meets the difficulty requirement using the EXACT same logic as the website
/// Website uses: (hashValue | target) === target
/// This checks if all bits set in hash are also set in target (hash is subset of target)
fn check_difficulty(hash: &[u8; 64], difficulty_mask: &[u8; 4]) -> bool {
    // Convert first 4 bytes of hash to u32 (big-endian, matching hex string interpretation)
    let hash_value = u32::from_be_bytes([hash[0], hash[1], hash[2], hash[3]]);

    // Convert difficulty mask to u32 (big-endian)
    let target = u32::from_be_bytes(*difficulty_mask);

    // Website's check: (hashValue | target) === target
    // This means: all bits in hashValue must be a subset of bits in target
    (hash_value | target) == target
}

/// Convert difficulty hex to human-readable level (matching website display)
pub fn difficulty_to_level(difficulty_hex: &str) -> &'static str {
    // Parse the difficulty as a u32 to count leading zero bits
    if let Ok(bytes) = hex::decode(difficulty_hex) {
        if bytes.len() >= 4 {
            let difficulty = u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
            let leading_zeros = difficulty.leading_zeros();
            
            // Match website's difficulty levels based on leading zero bits
            match leading_zeros {
                0..=3 => "Impossible",
                4..=7 => "Extreme",
                8..=11 => "Very Hard",
                12..=14 => "Hard",
                15..=16 => "Medium",
                17..=18 => "Easy",
                19..=20 => "Very Easy",
                _ => "Trivial",
            }
        } else {
            "Unknown"
        }
    } else {
        "Unknown"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_difficulty() {
        let difficulty = "000FFFFF";
        let mask = parse_difficulty(difficulty).unwrap();
        assert_eq!(mask, [0x00, 0x0F, 0xFF, 0xFF]);
    }

    #[test]
    fn test_check_difficulty() {
        let target = [0x00, 0x0F, 0xFF, 0xFF];

        // This should pass: hash < target (first byte 0x00, second 0x06 < 0x0F)
        let mut hash = [0u8; 64];
        hash[0] = 0x00;
        hash[1] = 0x06;
        assert!(check_difficulty(&hash, &target));

        // This should pass: hash == target exactly
        hash[0] = 0x00;
        hash[1] = 0x0F;
        hash[2] = 0xFF;
        hash[3] = 0xFF;
        assert!(check_difficulty(&hash, &target));

        // This should fail: hash > target (second byte 0x10 > 0x0F)
        hash[0] = 0x00;
        hash[1] = 0x10;
        assert!(!check_difficulty(&hash, &target));

        // This should fail: first byte > 0x00
        hash[0] = 0x01;
        hash[1] = 0x00;
        assert!(!check_difficulty(&hash, &target));
    }

    #[test]
    fn test_construct_preimage() {
        let challenge = Challenge {
            challenge_id: "**D07C10".to_string(),
            day: 7,
            challenge_number: 10,
            issued_at: chrono::Utc::now(),
            latest_submission: "2025-10-19T08:59:59.000Z".to_string(),
            difficulty: "000FFFFF".to_string(),
            no_pre_mine: "fd651ac2725e3b9d804cc8b161c0709af14d6264f93e8d4afef0fd1142a3f011"
                .to_string(),
            no_pre_mine_hour: "509681483".to_string(),
        };

        let address = "addr_test1qq4dl3nhr0axurgcrpun9xyp04pd2r2dwu5x7eeam98psv6dhxlde8ucclv2p46hm077ds4vzelf5565fg3ky794uhrq5up0he";
        let nonce = 0x0019c96b6a30ee38u64;

        let preimage = construct_preimage(nonce, address, &challenge);
        let preimage_str = String::from_utf8(preimage).unwrap();

        assert!(preimage_str.starts_with("0019c96b6a30ee38"));
        assert!(preimage_str.contains(address));
        assert!(preimage_str.contains("**D07C10"));
    }
}
