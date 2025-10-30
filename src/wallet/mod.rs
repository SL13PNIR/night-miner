use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use tracing::{debug, info};

/// Wallet configuration for signing messages
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WalletConfig {
    pub address: String,
    pub signing_key: String,      // Hex-encoded private key
    pub verification_key: String, // Hex-encoded public key (short form, 64 chars)
}

impl WalletConfig {
    /// Load wallet configuration from a JSON file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents = fs::read_to_string(path.as_ref())
            .context("Failed to read wallet configuration file")?;

        let config: WalletConfig =
            serde_json::from_str(&contents).context("Failed to parse wallet configuration")?;

        info!(
            "Loaded wallet configuration for address: {}",
            config.address
        );
        Ok(config)
    }

    /// Save wallet configuration to a JSON file
    pub fn to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let contents = serde_json::to_string_pretty(self)
            .context("Failed to serialize wallet configuration")?;

        fs::write(path.as_ref(), contents).context("Failed to write wallet configuration file")?;

        info!("Saved wallet configuration to: {:?}", path.as_ref());
        Ok(())
    }

    /// Get the short-form public key (64 hex characters)
    pub fn get_pubkey(&self) -> &str {
        &self.verification_key
    }

    /// Get the Cardano address
    pub fn get_address(&self) -> &str {
        &self.address
    }
}

/// Sign a message using CIP-8/30 standard
///
/// This creates a COSE_Sign1 structure as required by the Cardano ecosystem
#[allow(dead_code)]
pub fn sign_message(message: &str, wallet: &WalletConfig) -> Result<String> {
    debug!("Signing message: {}", message);

    // In a production environment, you would use proper Cardano signing libraries
    // This is a placeholder that shows the structure needed

    // For now, we'll return a note that external signing is required
    // In practice, you'd use cardano-cli, a hardware wallet, or cardano-serialization-lib

    anyhow::bail!(
        "Message signing requires external wallet integration.\n\
        Please use cardano-cli or your wallet software to sign the following message:\n\
        Message: {}\n\
        Address: {}\n\
        \n\
        Example using cardano-cli:\n\
        cardano-cli address key-sign \\\n\
          --signing-key-file payment.skey \\\n\
          --address {} \\\n\
          --message '{}' \\\n\
          --out-file signature.json",
        message,
        wallet.address,
        wallet.address,
        message
    );
}

/// Verify that a signature matches the expected format
#[allow(dead_code)]
pub fn verify_signature_format(signature: &str) -> Result<()> {
    // CIP-8/30 signatures are CBOR-encoded COSE_Sign1 structures
    // They should be hex-encoded and start with specific bytes

    let sig_bytes = hex::decode(signature).context("Signature must be valid hex")?;

    // COSE_Sign1 structures typically start with 0x84 (CBOR array of 4 elements)
    // or 0x85 (CBOR array of 5 elements)
    if sig_bytes.is_empty() {
        anyhow::bail!("Signature is empty");
    }

    if sig_bytes[0] != 0x84 && sig_bytes[0] != 0x85 {
        anyhow::bail!("Signature does not appear to be a valid COSE_Sign1 structure");
    }

    debug!("Signature format appears valid");
    Ok(())
}

/// Create a donation message for signing
#[allow(dead_code)]
pub fn create_donation_message(destination_address: &str) -> String {
    format!(
        "Assign accumulated Scavenger rights to: {}",
        destination_address
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_donation_message_format() {
        let addr = "addr1qq4dl3nhr0axurgcrpun9xyp04pd2r2dwu5x7eeam98psv6dhxlde8ucclv2p46hm077ds4vzelf5565fg3ky794uhrq5up0he";
        let message = create_donation_message(addr);
        assert_eq!(
            message,
            format!("Assign accumulated Scavenger rights to: {}", addr)
        );
    }

    #[test]
    fn test_verify_signature_format_valid() {
        // Example signature from documentation
        let sig = "845882a30127045839001c2e057143337716055394074256b79df7fc36051802ccefc1b2d3bf2a77372b1cff16a2cfe1e9a634bfaae3c74e8c8188e6043f572295f067616464726573735839001c2e057143337716055394074256b79df7fc36051802ccefc1b2d3bf2a77372b1cff16a2cfe1e9a634bfaae3c74e8c8188e6043f572295f0a166686173686564f458b34920616772656520746f20616269646520627920746865207465726d7320616e6420636f6e646974696f6e732061732064657363726962656420696e2076657273696f6e20312d30206f6620746865204d69646e696768742073636176656e676572206d696e696e672070726f636573733a206665666533366266386535666234363136636335363861386437626132306162373063616266326538376238663836616563623936623032643833656434386665584050a01e23e3a6cefcb93901af88f9873421fa76f75f98d7d0c7b43b3bdf09676921d7ee326f3bf1061fea4c62e07b84b9fdd1e17cd5d52790a7c1a0fce99e80e";
        assert!(verify_signature_format(sig).is_ok());
    }

    #[test]
    fn test_verify_signature_format_invalid() {
        let sig = "invalid";
        assert!(verify_signature_format(sig).is_err());
    }
}
