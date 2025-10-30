use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Response from GET /TandC endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TermsAndConditions {
    pub version: String,
    pub content: String,
    pub message: String,
}

/// Response from POST /register endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RegistrationResponse {
    pub registration_receipt: RegistrationReceipt,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistrationReceipt {
    pub preimage: String,
    pub signature: String,
    pub timestamp: DateTime<Utc>,
}

/// Response from GET /challenge endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeResponse {
    pub code: ChallengeStatus,
    #[serde(flatten)]
    pub data: ChallengeData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ChallengeStatus {
    Before,
    Active,
    After,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ChallengeData {
    Before {
        starts_at: DateTime<Utc>,
    },
    Active {
        challenge: Challenge,
        mining_period_ends: DateTime<Utc>,
        max_day: u32,
        total_challenges: u32,
        current_day: u32,
        next_challenge_starts_at: DateTime<Utc>,
    },
    After,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Challenge {
    pub challenge_id: String,
    pub day: u32,
    pub challenge_number: u32,
    pub issued_at: DateTime<Utc>,
    pub latest_submission: String, // ISO 8601 date string
    pub difficulty: String,
    pub no_pre_mine: String,
    pub no_pre_mine_hour: String,
}

/// Response from POST /solution endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SolutionResponse {
    pub crypto_receipt: CryptoReceipt,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CryptoReceipt {
    pub preimage: String,
    pub timestamp: DateTime<Utc>,
    pub signature: String,
}

/// Response from POST /donate_to endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DonationResponse {
    pub status: String,
    pub message: String,
    pub donation_id: String,
    pub original_address: String,
    pub destination_address: String,
    pub timestamp: DateTime<Utc>,
    pub solutions_consolidated: u32,
}

/// Response from GET /work_to_star_rate endpoint
pub type WorkToStarRate = Vec<u64>;

/// Response from GET /statistics/{address} endpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatisticsResponse {
    pub global: GlobalStatistics,
    pub local: LocalStatistics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalStatistics {
    pub wallets: u64,
    pub challenges: u32,
    pub total_challenges: u32,
    pub total_crypto_receipts: u64,
    pub recent_crypto_receipts: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalStatistics {
    pub crypto_receipts: u32,
    pub night_allocation: u64,
}

/// Error response from API
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiError {
    pub message: String,
    pub error: String,
    #[serde(rename = "statusCode")]
    pub status_code: u16,
}
