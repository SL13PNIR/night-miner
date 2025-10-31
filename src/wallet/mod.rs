use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::process::Command;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressEntry {
    pub address: String,
    pub verification_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WalletConfig {
    pub addresses: Vec<AddressEntry>,
}

impl WalletConfig {
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents = fs::read_to_string(path.as_ref())
            .context("Failed to read wallet configuration file")?;
        let config: WalletConfig =
            serde_json::from_str(&contents).context("Failed to parse wallet configuration")?;
        if config.addresses.is_empty() {
            anyhow::bail!("Wallet must have at least one address");
        }
        info!("Loaded wallet configuration with {} address(es)", config.addresses.len());
        for (i, entry) in config.addresses.iter().enumerate() {
            info!("  [{}] {}", i, entry.address);
        }
        Ok(config)
    }

    pub fn to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let contents = serde_json::to_string_pretty(self)
            .context("Failed to serialize wallet configuration")?;
        fs::write(path.as_ref(), contents).context("Failed to write wallet configuration file")?;
        info!("Saved wallet configuration to: {:?}", path.as_ref());
        Ok(())
    }

    pub fn get_primary_address(&self) -> &str {
        &self.addresses[0].address
    }
    
    pub fn get_primary_pubkey(&self) -> &str {
        &self.addresses[0].verification_key
    }
    
    pub fn get_addresses(&self) -> &[AddressEntry] {
        &self.addresses
    }
    
    pub fn address_count(&self) -> usize {
        self.addresses.len()
    }
    
    pub fn get_pubkey_for_address(&self, address: &str) -> Option<&str> {
        self.addresses
            .iter()
            .find(|entry| entry.address == address)
            .map(|entry| entry.verification_key.as_str())
    }
}

pub fn sign_message_with_key<P: AsRef<Path>>(message: &str, address: &str, signing_key_path: P) -> Result<String> {
    use cardano_serialization_lib::PrivateKey;
    use serde_cbor::Value as CborValue;
    
    let key_content = fs::read_to_string(signing_key_path.as_ref()).context("Failed to read signing key file")?;
    let key_json: serde_json::Value = serde_json::from_str(&key_content).context("Failed to parse signing key JSON")?;
    let cbor_hex = key_json["cborHex"].as_str().context("Missing cborHex field in signing key")?;
    let cbor_bytes = hex::decode(cbor_hex).context("Failed to decode cborHex")?;
    let private_key = PrivateKey::from_normal_bytes(&cbor_bytes[2..34]).map_err(|e| anyhow::anyhow!("Failed to parse private key: {:?}", e))?;
    
    let (_, addr_data) = bech32::decode(address).map_err(|e| anyhow::anyhow!("Failed to decode bech32 address: {}", e))?;
    let addr_bytes = addr_data;
    
    // CIP-8: The payload is just the message bytes
    // The "hashed": false flag goes in the UNPROTECTED headers, not the payload!
    let message_bytes = message.as_bytes().to_vec();
    let payload_cbor = message_bytes.clone();
    
    let protected_map_cbor = {
        let mut map = std::collections::BTreeMap::new();
        map.insert(CborValue::Integer(1), CborValue::Integer(-8));
        map.insert(CborValue::Text("address".to_string()), CborValue::Bytes(addr_bytes));
        serde_cbor::to_vec(&CborValue::Map(map))?
    };
    
    let sig_structure = CborValue::Array(vec![
        CborValue::Text("Signature1".to_string()),
        CborValue::Bytes(protected_map_cbor.clone()),
        CborValue::Bytes(vec![]),
        CborValue::Bytes(payload_cbor.clone()),
    ]);
    let sig_structure_cbor = serde_cbor::to_vec(&sig_structure)?;
    
    let signature = private_key.sign(&sig_structure_cbor);
    let signature_bytes = signature.to_bytes();
    
    // CIP-8: Add "hashed": false to unprotected headers
    let unprotected_map = {
        let mut map = std::collections::BTreeMap::new();
        map.insert(CborValue::Text("hashed".to_string()), CborValue::Bool(false));
        CborValue::Map(map)
    };
    
    // CIP-8 uses plain COSE_Sign1 (no Tag 98 wrapper like CIP-30)
    let cose_sign1 = CborValue::Array(vec![
        CborValue::Bytes(protected_map_cbor),
        unprotected_map,
        CborValue::Bytes(payload_cbor),
        CborValue::Bytes(signature_bytes.to_vec()),
    ]);
    
    let signature_cbor = serde_cbor::to_vec(&cose_sign1)?;
    Ok(hex::encode(signature_cbor))
}

pub fn derive_address_from_key<P: AsRef<Path>>(signing_key_path: P, wallet_dir: P) -> Result<String> {
    let skey_path = signing_key_path.as_ref();
    let vkey_path = skey_path.with_extension("vkey");
    if !vkey_path.exists() {
        anyhow::bail!("Verification key file not found: {:?}", vkey_path);
    }
    let wallet_dir = wallet_dir.as_ref();
    let stake_vkey = if let Ok(entries) = std::fs::read_dir(wallet_dir) {
        entries
            .filter_map(|entry| entry.ok())
            .map(|entry| entry.path())
            .find(|path| {
                path.extension().map_or(false, |ext| ext == "vkey")
                    && path.file_stem()
                        .and_then(|s| s.to_str())
                        .map_or(false, |s| s.ends_with("-stake"))
            })
    } else {
        None
    };
    let stake_vkey = stake_vkey.context("Stake verification key not found. Expected a file ending with -stake.vkey")?;
    info!("Using stake key: {:?}", stake_vkey);
    let output = Command::new("cardano-cli")
        .args(&["address", "build", "--payment-verification-key-file", vkey_path.to_str().unwrap(), "--stake-verification-key-file", stake_vkey.to_str().unwrap(), "--mainnet"])
        .output()
        .context("Failed to execute cardano-cli")?;
    if !output.status.success() {
        anyhow::bail!("Failed to derive address: {}", String::from_utf8_lossy(&output.stderr));
    }
    Ok(String::from_utf8(output.stdout)?.trim().to_string())
}

/// Create and sign a donation message
/// Message format: "Assign accumulated Scavenger rights to: <destination_address>"
pub fn sign_donation_message<P: AsRef<Path>>(
    destination_address: &str,
    original_address: &str,
    signing_key_path: P,
) -> Result<String> {
    let message = format!("Assign accumulated Scavenger rights to: {}", destination_address);
    sign_message_with_key(&message, original_address, signing_key_path)
}
