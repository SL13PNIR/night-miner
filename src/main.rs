mod api;
mod config;
mod coordinator;
mod miner;
mod wallet;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use config::Config;
use coordinator::MiningCoordinator;
use wallet::WalletConfig;

/// NIGHT Token Scavenger Mine - Optimized Mining Client
#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Path to configuration file
    #[arg(short, long, value_name = "FILE")]
    config: Option<PathBuf>,

    /// Path to wallet configuration file
    #[arg(short, long, value_name = "FILE")]
    wallet: Option<PathBuf>,

    /// Number of mining threads (defaults to CPU count)
    #[arg(short, long)]
    threads: Option<usize>,

    /// Log level (trace, debug, info, warn, error)
    #[arg(short, long, default_value = "info")]
    log_level: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start mining for NIGHT tokens
    Mine {
        /// Timeout for each challenge in minutes
        #[arg(short = 't', long, default_value = "55")]
        timeout: u64,
    },

    /// Register your wallet address with the Scavenger Mine service
    Register {
        /// CIP-8/30 signature over the T&C message
        #[arg(short, long)]
        signature: String,

        /// Specific address to register (defaults to primary/first address)
        #[arg(short = 'a', long)]
        address: Option<String>,
    },

    /// Fetch the current challenge information
    Challenge,

    /// Fetch the Terms and Conditions
    #[command(name = "tandc")]
    TermsAndConditions {
        /// Version of T&C to fetch
        #[arg(short, long)]
        version: Option<String>,
    },

    /// Fetch work-to-STAR conversion rates
    Rates,

    /// Donate/consolidate solutions to another address
    Donate {
        /// Destination address to receive the solutions
        #[arg(short, long)]
        destination: String,

        /// CIP-8/30 signature over the donation message
        #[arg(short, long)]
        signature: String,

        /// Specific address to donate from (defaults to primary/first address)
        #[arg(short = 'a', long)]
        address: Option<String>,
    },

    /// Create wallet, register all addresses, and set up donations to destination
    BulkDonate {
        /// Destination address to receive all donations (overrides donation-address.json)
        #[arg(short, long)]
        destination: Option<String>,

        /// Path to donation-address.json file
        #[arg(short = 'f', long, default_value = "donation-address.json")]
        donation_address_file: PathBuf,

        /// Number of addresses to create (including the donor address)
        #[arg(short = 'n', long, default_value = "1")]
        count: usize,

        /// Output directory for wallet files
        #[arg(short = 'o', long, default_value = "bulk-donation-wallet")]
        output_dir: PathBuf,

        /// Wallet name prefix
        #[arg(short = 'w', long, default_value = "addr")]
        wallet_name: String,
    },

    /// Generate a sample configuration file
    InitConfig {
        /// Output path for the configuration file
        #[arg(short, long, default_value = "config.toml")]
        output: PathBuf,
    },

    /// Generate a sample wallet configuration template
    InitWallet {
        /// Output path for the wallet configuration file
        #[arg(short, long, default_value = "wallet.json")]
        output: PathBuf,
    },

    /// Create a new wallet using cardano-cli
    CreateWallet {
        /// Name for the wallet (used for file naming)
        #[arg(short, long, default_value = "payment")]
        name: String,

        /// Output directory for wallet files
        #[arg(short, long, default_value = ".")]
        output_dir: PathBuf,

        /// Network: mainnet or testnet
        #[arg(short = 'n', long, default_value = "mainnet")]
        network: String,
    },

    /// Sign a message using your wallet's signing key
    Sign {
        /// Message to sign (if not provided, fetches current T&C message from API)
        #[arg(short, long)]
        message: Option<String>,

        /// Path to signing key file (Cardano .skey format)
        #[arg(short = 'k', long)]
        signing_key: Option<PathBuf>,

        /// Specific address to sign with (defaults to primary/first address)
        #[arg(short = 'a', long)]
        address: Option<String>,

        /// Output the signature to stdout instead of pretty format
        #[arg(short = 'o', long)]
        stdout: bool,
    },

    /// Add a new address to an existing wallet
    AddAddress {
        /// Name for the new address (used for file naming)
        #[arg(short, long)]
        name: String,

        /// Directory containing the wallet.json file
        #[arg(short = 'd', long, default_value = ".")]
        wallet_dir: PathBuf,

        /// Network: mainnet or testnet
        #[arg(short = 'n', long, default_value = "mainnet")]
        network: String,
    },

    /// Automated mining workflow: creates wallet, mines, auto-rotates addresses per solution
    AutoMine {
        /// Output directory for wallet files
        #[arg(short = 'o', long, default_value = "auto-mine-wallet")]
        output_dir: PathBuf,

        /// Network: mainnet or testnet
        #[arg(short = 'n', long, default_value = "mainnet")]
        network: String,

        /// Number of mining threads (defaults to CPU count)
        #[arg(short, long)]
        threads: Option<usize>,

        /// Challenge timeout in minutes
        #[arg(short = 't', long, default_value = "55")]
        timeout: u64,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize tracing/logging
    init_logging(&cli.log_level)?;

    match cli.command {
        Commands::Mine { timeout } => {
            info!("Starting NIGHT Token Miner");

            // Load configuration
            let mut config = if let Some(config_path) = cli.config {
                Config::from_file(config_path)?
            } else {
                Config::default()
            };

            // Override with CLI arguments
            if let Some(threads) = cli.threads {
                config.threads = Some(threads);
            }
            config.challenge_timeout_minutes = Some(timeout);

            // Validate configuration
            config.validate()?;

            // Load wallet
            let wallet_path = cli
                .wallet
                .or_else(|| Some(PathBuf::from(&config.wallet_config_path)))
                .context("Wallet configuration path not specified")?;

            let wallet = WalletConfig::from_file(wallet_path)?;

            info!("Mining with address: {}", wallet.get_primary_address());
            info!(
                "Using {} threads",
                config.threads.unwrap_or_else(num_cpus::get)
            );
            info!(
                "Challenge timeout: {} minutes",
                config.challenge_timeout_minutes.unwrap_or(55)
            );

            // Create and run coordinator
            let mut coordinator =
                MiningCoordinator::new(wallet, config.threads, config.challenge_timeout_minutes)?;

            coordinator.run().await?;
        }

        Commands::Register { signature, address } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(wallet_path)?;

            // Determine which address to register
            let (reg_address, reg_pubkey) = if let Some(addr) = address {
                let pubkey = wallet
                    .get_pubkey_for_address(&addr)
                    .context(format!("Address {} not found in wallet", addr))?;
                (addr, pubkey.to_string())
            } else {
                (wallet.get_primary_address().to_string(), wallet.get_primary_pubkey().to_string())
            };

            let client = api::ScavengerClient::new()?;

            info!("Registering address: {}", reg_address);

            let response = client
                .register(&reg_address, &signature, &reg_pubkey)
                .await?;

            info!("Registration successful!");
            info!(
                "Receipt timestamp: {}",
                response.registration_receipt.timestamp
            );
            info!(
                "Receipt signature: {}",
                response.registration_receipt.signature
            );
        }

        Commands::Challenge => {
            let client = api::ScavengerClient::new()?;
            let response = client.get_challenge().await?;

            // Print JSON response
            println!("{}", serde_json::to_string_pretty(&response)?);
            
            // If active, show difficulty level
            if let api::ChallengeData::Active { challenge, .. } = &response.data {
                let level = miner::difficulty_to_level(&challenge.difficulty);
                println!("\n💡 Difficulty Level: {}", level);
            }
        }

        Commands::TermsAndConditions { version } => {
            let client = api::ScavengerClient::new()?;
            let tandc = client.get_terms_and_conditions(version.as_deref()).await?;

            println!("Version: {}", tandc.version);
            println!("\n{}", tandc.content);
            println!("\nMessage to sign:");
            println!("{}", tandc.message);
        }

        Commands::Rates => {
            let client = api::ScavengerClient::new()?;
            let rates = client.get_work_to_star_rate().await?;

            println!("Daily STAR rates:");
            for (day, rate) in rates.iter().enumerate() {
                println!(
                    "Day {}: {} STAR ({:.6} NIGHT)",
                    day + 1,
                    rate,
                    *rate as f64 / 1_000_000.0
                );
            }

            if !rates.is_empty() {
                let total: u64 = rates.iter().sum();
                println!(
                    "\nTotal so far: {} STAR ({:.6} NIGHT)",
                    total,
                    total as f64 / 1_000_000.0
                );
            }
        }

        Commands::Donate {
            destination,
            signature,
            address,
        } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(wallet_path)?;

            // Determine which address to donate from
            let original_address = if let Some(addr) = address {
                // Verify address exists in wallet
                wallet
                    .get_pubkey_for_address(&addr)
                    .context(format!("Address {} not found in wallet", addr))?;
                addr
            } else {
                wallet.get_primary_address().to_string()
            };

            let client = api::ScavengerClient::new()?;

            info!("Donating from {} to {}", original_address, destination);

            let response = client
                .donate_to(&destination, &original_address, &signature)
                .await?;

            info!("Donation successful!");
            info!(
                "Solutions consolidated: {}",
                response.solutions_consolidated
            );
            info!("Donation ID: {}", response.donation_id);
        }

        Commands::InitConfig { output } => {
            let config = Config::default();
            config.save(&output)?;
            info!("Created sample configuration at: {:?}", output);
            println!("Edit the configuration file and update the wallet_config_path");
        }

        Commands::InitWallet { output } => {
            // Create a template wallet config with new structure
            let wallet = WalletConfig {
                addresses: vec![wallet::AddressEntry {
                    address: "addr1q8upjxynn626c772r5nzym...".to_string(),
                    verification_key: "YOUR_PUBLIC_KEY_HEX_64_CHARS".to_string(),
                }],
                challenge_submissions: HashMap::new(),
            };

            wallet.to_file(&output)?;
            info!("Created wallet configuration template at: {:?}", output);
            println!("\n⚠️  IMPORTANT: Update the wallet.json file with your actual:");
            println!("  - Cardano addresses");
            println!("  - Public keys (64-character hex format for each address)");
            println!("  - Add multiple addresses to mine in parallel");
        }

        Commands::CreateWallet {
            name,
            output_dir,
            network,
        } => {
            use std::process::Command;
            use std::fs;

            // Check if cardano-cli is available
            let cli_paths = vec![
                "cardano-cli",
                ".\\bin\\cardano-cli.exe",
                "./bin/cardano-cli",
            ];
            
            let mut cardano_cli = None;
            for path in &cli_paths {
                let check = Command::new(path)
                    .arg("--version")
                    .output();
                    
                if let Ok(output) = check {
                    if output.status.success() {
                        cardano_cli = Some(path.to_string());
                        let version = String::from_utf8_lossy(&output.stdout);
                        info!("Found cardano-cli: {}", version.trim());
                        break;
                    }
                }
            }
            
            let cardano_cli = cardano_cli.context(
                "cardano-cli not found. Please install Cardano CLI:\n\
                - Windows: Download from https://github.com/IntersectMBO/cardano-node/releases\n\
                - Linux: sudo apt install cardano-cli\n\
                - macOS: brew install cardano-cli\n\
                Or place cardano-cli.exe in the ./bin directory"
            )?;

            // Create output directory
            fs::create_dir_all(&output_dir)?;
            
            let payment_vkey = output_dir.join(format!("{}.vkey", name));
            let payment_skey = output_dir.join(format!("{}.skey", name));
            let stake_vkey = output_dir.join(format!("{}-stake.vkey", name));
            let stake_skey = output_dir.join(format!("{}-stake.skey", name));
            let payment_addr = output_dir.join(format!("{}.addr", name));

            println!("🔧 Creating Cardano wallet...\n");

            // Generate payment key pair
            info!("Generating payment key pair...");
            let payment_output = Command::new(&cardano_cli)
                .args(&[
                    "address", "key-gen",
                    "--verification-key-file", payment_vkey.to_str().unwrap(),
                    "--signing-key-file", payment_skey.to_str().unwrap(),
                ])
                .output()?;

            if !payment_output.status.success() {
                anyhow::bail!(
                    "Failed to generate payment keys: {}",
                    String::from_utf8_lossy(&payment_output.stderr)
                );
            }
            println!("✅ Payment keys generated");

            // Generate stake key pair
            info!("Generating stake key pair...");
            let stake_output = Command::new(&cardano_cli)
                .args(&[
                    "stake-address", "key-gen",
                    "--verification-key-file", stake_vkey.to_str().unwrap(),
                    "--signing-key-file", stake_skey.to_str().unwrap(),
                ])
                .output()?;

            if !stake_output.status.success() {
                anyhow::bail!(
                    "Failed to generate stake keys: {}",
                    String::from_utf8_lossy(&stake_output.stderr)
                );
            }
            println!("✅ Stake keys generated");

            // Build payment address
            info!("Building payment address...");
            
            let mut addr_args = vec![
                "address".to_string(), "build".to_string(),
                "--payment-verification-key-file".to_string(), payment_vkey.to_str().unwrap().to_string(),
                "--stake-verification-key-file".to_string(), stake_vkey.to_str().unwrap().to_string(),
            ];
            
            if network == "mainnet" {
                addr_args.push("--mainnet".to_string());
            } else {
                addr_args.push("--testnet-magic".to_string());
                addr_args.push("1".to_string()); // Preprod testnet
            }
            
            addr_args.push("--out-file".to_string());
            addr_args.push(payment_addr.to_str().unwrap().to_string());

            let addr_output = Command::new(&cardano_cli)
                .args(&addr_args)
                .output()?;

            if !addr_output.status.success() {
                anyhow::bail!(
                    "Failed to build address: {}",
                    String::from_utf8_lossy(&addr_output.stderr)
                );
            }

            // Read the generated address
            let address = fs::read_to_string(&payment_addr)?.trim().to_string();
            println!("✅ Address generated: {}", address);

            // Extract verification key (public key)
            let vkey_content = fs::read_to_string(&payment_vkey)?;
            let vkey_json: serde_json::Value = serde_json::from_str(&vkey_content)?;
            let vkey_hex = vkey_json["cborHex"]
                .as_str()
                .context("Failed to extract verification key")?;
            
            // The verification key is CBOR-encoded, we need to decode it
            let vkey_bytes = hex::decode(vkey_hex)?;
            // Skip CBOR wrapper (first 2 bytes: type + length), take 32 bytes of public key
            let pubkey_hex = if vkey_bytes.len() >= 34 {
                hex::encode(&vkey_bytes[2..34])
            } else {
                hex::encode(&vkey_bytes[..])
            };

            println!("✅ Verification key: {}", pubkey_hex);

            // Create wallet.json
            let wallet_json = output_dir.join("wallet.json");

            let wallet = WalletConfig {
                addresses: vec![wallet::AddressEntry {
                    address: address.clone(),
                    verification_key: pubkey_hex.clone(),
                }],
                challenge_submissions: HashMap::new(),
            };

            wallet.to_file(&wallet_json)?;

            println!("\n✅ Wallet created successfully!");
            println!("\n📁 Files created:");
            println!("   Payment verification key: {}", payment_vkey.display());
            println!("   Payment signing key:      {}", payment_skey.display());
            println!("   Stake verification key:   {}", stake_vkey.display());
            println!("   Stake signing key:        {}", stake_skey.display());
            println!("   Payment address:          {}", payment_addr.display());
            println!("   Wallet config:            {}", wallet_json.display());

            println!("\n🔐 SECURITY:");
            println!("   ⚠️  Keep your .skey files secure and private!");
            println!("   ⚠️  Back them up securely!");
            println!("   ⚠️  Never share your signing keys!");

            println!("\n📋 Next steps:");
            println!("   1. Sign the T&C (automatically fetches current message from API):");
            println!("      night-miner --wallet {} sign --signing-key {}", 
                     wallet_json.display(), payment_skey.display());
            println!("   2. Register with signature:");
            println!("      night-miner --wallet {} register --signature \"<signature>\"", 
                     wallet_json.display());
            println!("   3. Start mining:");
            println!("      night-miner --wallet {} mine", wallet_json.display());
        }

        Commands::Sign {
            message,
            signing_key,
            address,
            stdout,
        } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(&wallet_path)?;

            // Determine which address to sign with
            let (sign_address, sign_pubkey) = if let Some(addr) = address {
                let pubkey = wallet
                    .get_pubkey_for_address(&addr)
                    .context(format!("Address {} not found in wallet", addr))?;
                (addr, pubkey.to_string())
            } else {
                (wallet.get_primary_address().to_string(), wallet.get_primary_pubkey().to_string())
            };

            // If no message provided, fetch from API
            let message = if let Some(msg) = message {
                msg
            } else {
                info!("No message provided, fetching current T&C from API...");
                let client = api::ScavengerClient::new()?;
                let tandc = client.get_terms_and_conditions(None).await?;
                info!("Fetched T&C version {}", tandc.version);
                if !stdout {
                    println!("📜 Using T&C message (version {}):", tandc.version);
                    println!("{}\n", tandc.message);
                }
                tandc.message
            };

            // Determine signing key path
            let key_path = if let Some(key) = signing_key {
                key
            } else {
                // Try common locations
                let candidates = vec![
                    PathBuf::from("payment.skey"),
                    PathBuf::from("test-wallet/test-wallet.skey"),
                    PathBuf::from("stake.skey"),
                ];

                candidates
                    .into_iter()
                    .find(|p| p.exists())
                    .context("No signing key file found. Please specify with --signing-key")?
            };

            info!("Signing message with key from: {:?}", key_path);
            info!("Using address from wallet: {}", sign_address);

            let signature = wallet::sign_message_with_key(&message, &sign_address, &key_path)?;

            if stdout {
                println!("{}", signature);
            } else {
                println!("✅ Signature generated successfully!");
                println!("\nFor address: {}", sign_address);
                println!("With pubkey: {}", sign_pubkey);
                println!("\nSignature:");
                println!("{}", signature);
                println!("\n💡 Use this to register:");
                println!("   night-miner --wallet {} register --signature \"{}\"", 
                         wallet_path.display(), signature);
            }
        }

        Commands::AddAddress {
            name,
            wallet_dir,
            network,
        } => {
            // Find cardano-cli
            let cli_paths = vec![
                "cardano-cli",
                "cardano-cli.exe",
                "./bin/cardano-cli",
                "./bin/cardano-cli.exe",
            ];
            
            let mut cardano_cli = None;
            for path in &cli_paths {
                let check = Command::new(path)
                    .arg("--version")
                    .output();
                    
                if let Ok(output) = check {
                    if output.status.success() {
                        cardano_cli = Some(path.to_string());
                        let version = String::from_utf8_lossy(&output.stdout);
                        info!("Found cardano-cli: {}", version.trim());
                        break;
                    }
                }
            }
            
            let cardano_cli = cardano_cli.context(
                "cardano-cli not found. Please install Cardano CLI."
            )?;

            // Load existing wallet config
            let wallet_json = wallet_dir.join("wallet.json");
            let mut wallet = WalletConfig::from_file(&wallet_json)?;

            let payment_vkey = wallet_dir.join(format!("{}.vkey", name));
            let payment_skey = wallet_dir.join(format!("{}.skey", name));
            let stake_vkey = wallet_dir.join(format!("{}-stake.vkey", name));
            let stake_skey = wallet_dir.join(format!("{}-stake.skey", name));
            let payment_addr = wallet_dir.join(format!("{}.addr", name));

            println!("🔧 Adding new address to wallet...\n");

            // Generate payment key pair
            info!("Generating payment key pair...");
            let payment_output = Command::new(&cardano_cli)
                .args(&[
                    "address", "key-gen",
                    "--verification-key-file", payment_vkey.to_str().unwrap(),
                    "--signing-key-file", payment_skey.to_str().unwrap(),
                ])
                .output()?;

            if !payment_output.status.success() {
                anyhow::bail!(
                    "Failed to generate payment keys: {}",
                    String::from_utf8_lossy(&payment_output.stderr)
                );
            }
            println!("✅ Payment keys generated");

            // Generate stake key pair
            info!("Generating stake key pair...");
            let stake_output = Command::new(&cardano_cli)
                .args(&[
                    "stake-address", "key-gen",
                    "--verification-key-file", stake_vkey.to_str().unwrap(),
                    "--signing-key-file", stake_skey.to_str().unwrap(),
                ])
                .output()?;

            if !stake_output.status.success() {
                anyhow::bail!(
                    "Failed to generate stake keys: {}",
                    String::from_utf8_lossy(&stake_output.stderr)
                );
            }
            println!("✅ Stake keys generated");

            // Build payment address
            info!("Building payment address...");
            let network_arg = match network.as_str() {
                "testnet" => "--testnet-magic 1",
                _ => "--mainnet",
            };

            let addr_output = Command::new(&cardano_cli)
                .args(&[
                    "address", "build",
                    "--payment-verification-key-file", payment_vkey.to_str().unwrap(),
                    "--stake-verification-key-file", stake_vkey.to_str().unwrap(),
                ])
                .args(network_arg.split_whitespace())
                .output()?;

            if !addr_output.status.success() {
                anyhow::bail!(
                    "Failed to build address: {}",
                    String::from_utf8_lossy(&addr_output.stderr)
                );
            }

            let address = String::from_utf8(addr_output.stdout)?
                .trim()
                .to_string();

            fs::write(&payment_addr, &address)?;
            println!("✅ Address generated: {}", address);

            // Read verification key to get public key
            let vkey_content = fs::read_to_string(&payment_vkey)?;
            let vkey_json: serde_json::Value = serde_json::from_str(&vkey_content)?;
            let pubkey_hex = vkey_json["cborHex"]
                .as_str()
                .context("Failed to extract public key from verification key")?
                .trim_start_matches("5820")
                .to_string();

            println!("✅ Verification key: {}", pubkey_hex);

            // Add new address to wallet config
            wallet.addresses.push(wallet::AddressEntry {
                address: address.clone(),
                verification_key: pubkey_hex.clone(),
            });

            wallet.to_file(&wallet_json)?;

            println!("\n✅ Address added successfully!");
            println!("\n📁 Files created:");
            println!("   Payment verification key: {}", payment_vkey.display());
            println!("   Payment signing key:      {}", payment_skey.display());
            println!("   Stake verification key:   {}", stake_vkey.display());
            println!("   Stake signing key:        {}", stake_skey.display());
            println!("   Payment address:          {}", payment_addr.display());
            println!("\n📋 Wallet now has {} address(es)", wallet.addresses.len());

            println!("\n🔐 SECURITY:");
            println!("   ⚠️  Keep your .skey files secure and private!");
            println!("   ⚠️  Back them up securely!");

            println!("\n📋 Next steps:");
            println!("   1. Sign the T&C for this address:");
            println!("      night-miner --wallet {} sign --signing-key {}", 
                     wallet_json.display(), payment_skey.display());
            println!("   2. Register with signature:");
            println!("      night-miner --wallet {} register --signature \"<signature>\"", 
                     wallet_json.display());
        }

        Commands::BulkDonate {
            destination,
            donation_address_file,
            count,
            output_dir,
            wallet_name,
        } => {
            if count < 1 {
                anyhow::bail!("Count must be at least 1");
            }

            // Determine destination address: CLI arg takes precedence over file
            let destination_addr = if let Some(dest) = destination {
                dest
            } else {
                // Try to load from donation-address.json
                let donation_config = config::DonationConfig::from_file(&donation_address_file)
                    .context(format!(
                        "Failed to load donation address from {}. Please provide --destination or create donation-address.json",
                        donation_address_file.display()
                    ))?;
                donation_config.destination_address
            };

            println!("🎯 Bulk Donation Setup");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("Destination: {}", destination_addr);
            println!("Creating {} address(es)...\n", count);

            // Find cardano-cli
            let cli_paths = vec![
                "cardano-cli",
                "cardano-cli.exe",
                "./bin/cardano-cli",
                "./bin/cardano-cli.exe",
            ];
            
            let mut cardano_cli = None;
            for path in &cli_paths {
                let check = Command::new(path).arg("--version").output();
                if let Ok(output) = check {
                    if output.status.success() {
                        cardano_cli = Some(path.to_string());
                        break;
                    }
                }
            }
            
            let cardano_cli = cardano_cli.context("cardano-cli not found")?;

            // Create output directory
            fs::create_dir_all(&output_dir)?;
            
            let mut wallet = WalletConfig {
                addresses: Vec::new(),
                challenge_submissions: HashMap::new(),
            };

            let wallet_json = output_dir.join("wallet.json");
            let client = api::ScavengerClient::new()?;

            // Track overall success
            let mut total_succeeded = 0;
            let mut total_failed = 0;

            // Process each address one at a time: create -> register -> donate
            for i in 0..count {
                let name = format!("{}-{}", wallet_name, i);
                println!("📝 Creating address {}/{}: {}", i + 1, count, name);

                let payment_vkey = output_dir.join(format!("{}.vkey", name));
                let payment_skey = output_dir.join(format!("{}.skey", name));
                let stake_vkey = output_dir.join(format!("{}-stake.vkey", name));
                let stake_skey = output_dir.join(format!("{}-stake.skey", name));
                let payment_addr = output_dir.join(format!("{}.addr", name));

                // Generate payment key pair
                let payment_output = Command::new(&cardano_cli)
                    .args(&[
                        "address", "key-gen",
                        "--verification-key-file", payment_vkey.to_str().unwrap(),
                        "--signing-key-file", payment_skey.to_str().unwrap(),
                    ])
                    .output()?;

                if !payment_output.status.success() {
                    anyhow::bail!("Failed to generate payment keys: {}", 
                        String::from_utf8_lossy(&payment_output.stderr));
                }

                // Generate stake key pair
                let stake_output = Command::new(&cardano_cli)
                    .args(&[
                        "stake-address", "key-gen",
                        "--verification-key-file", stake_vkey.to_str().unwrap(),
                        "--signing-key-file", stake_skey.to_str().unwrap(),
                    ])
                    .output()?;

                if !stake_output.status.success() {
                    anyhow::bail!("Failed to generate stake keys: {}", 
                        String::from_utf8_lossy(&stake_output.stderr));
                }

                // Build payment address
                let addr_output = Command::new(&cardano_cli)
                    .args(&[
                        "address", "build",
                        "--payment-verification-key-file", payment_vkey.to_str().unwrap(),
                        "--stake-verification-key-file", stake_vkey.to_str().unwrap(),
                        "--mainnet",
                    ])
                    .output()?;

                if !addr_output.status.success() {
                    anyhow::bail!("Failed to build address: {}", 
                        String::from_utf8_lossy(&addr_output.stderr));
                }

                let address = String::from_utf8(addr_output.stdout)?.trim().to_string();
                fs::write(&payment_addr, &address)?;

                // Read verification key to get public key
                let vkey_content = fs::read_to_string(&payment_vkey)?;
                let vkey_json: serde_json::Value = serde_json::from_str(&vkey_content)?;
                let pubkey_hex = vkey_json["cborHex"]
                    .as_str()
                    .context("Failed to extract public key")?
                    .trim_start_matches("5820")
                    .to_string();

                let entry = wallet::AddressEntry {
                    address: address.clone(),
                    verification_key: pubkey_hex.clone(),
                };
                
                wallet.addresses.push(entry);
                wallet.to_file(&wallet_json)?;

                println!("   ✅ Created: {}", address);

                // Now immediately register this address
                println!("🔐 Registering address {}/{}...", i + 1, count);
                
                let mut address_fully_configured = false;
                
                // Sign T&C
                let tandc = client.get_terms_and_conditions(None).await?;
                let reg_signature = wallet::sign_message_with_key(
                    &tandc.message,
                    &address,
                    &payment_skey,
                )?;

                // Register with retry logic
                let mut attempt = 0;
                let max_attempts = 3;
                let mut registered = false;

                while attempt < max_attempts && !registered {
                    attempt += 1;
                    
                    match client.register(&address, &reg_signature, &pubkey_hex).await {
                        Ok(_) => {
                            println!("   ✅ Registered as miner");
                            registered = true;
                        }
                        Err(e) => {
                            let err_msg = e.to_string();
                            if err_msg.contains("Too Many Requests") || err_msg.contains("429") {
                                if attempt < max_attempts {
                                    println!("   ⏳ Rate limited, waiting 5 seconds... (attempt {}/{})", attempt, max_attempts);
                                    tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                                } else {
                                    println!("   ❌ Registration failed after {} attempts: {}", max_attempts, e);
                                }
                            } else {
                                println!("   ❌ Registration failed: {}", e);
                                break;
                            }
                        }
                    }
                }

                // If registration succeeded, register the donation
                if registered {
                    println!("💝 Registering donation to {}...", destination_addr);
                    
                    // Sign donation message
                    let donation_signature = wallet::sign_donation_message(
                        &destination_addr,
                        &address,
                        &payment_skey,
                    )?;

                    // Donate with retry logic
                    let mut attempt = 0;
                    let max_attempts = 3;
                    let mut donated = false;

                    while attempt < max_attempts && !donated {
                        attempt += 1;
                        
                        match client.donate_to(&destination_addr, &address, &donation_signature).await {
                            Ok(response) => {
                                println!("   ✅ Donation registered");
                                println!("      Solutions: {}", response.solutions_consolidated);
                                println!("      ID: {}", response.donation_id);
                                donated = true;
                                address_fully_configured = true;
                            }
                            Err(e) => {
                                let err_msg = e.to_string();
                                if err_msg.contains("Too Many Requests") || err_msg.contains("429") {
                                    if attempt < max_attempts {
                                        println!("   ⏳ Rate limited, waiting 5 seconds... (attempt {}/{})", attempt, max_attempts);
                                        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                                    } else {
                                        println!("   ❌ Donation failed after {} attempts: {}", max_attempts, e);
                                    }
                                } else {
                                    // Not a rate limit error, likely 403 Forbidden or other error
                                    println!("   ⚠️  Donation registration failed: {}", e);
                                    if err_msg.contains("403") || err_msg.contains("Forbidden") {
                                        println!("   ℹ️  This is normal - address needs to mine first to accumulate solutions");
                                        // Still consider it configured since mining registration succeeded
                                        address_fully_configured = true;
                                    }
                                    break;
                                }
                            }
                        }
                    }

                    if !donated && address_fully_configured {
                        println!("   ℹ️  Retry donation later with:");
                        println!("      night-miner --wallet {} donate --destination {} --signature \"{}\" --address {}", 
                                 wallet_json.display(), destination_addr, donation_signature, address);
                    }
                } else {
                    println!("   ⚠️  Skipping donation registration (mining registration failed)");
                }

                // Track overall success
                if address_fully_configured {
                    total_succeeded += 1;
                } else {
                    total_failed += 1;
                }

                // Add delay before next address to avoid rate limiting
                if i < count - 1 {
                    println!("");
                    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                }
            }

            // Summary
            println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("📊 Summary");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("📁 Wallet: {}", wallet_json.display());
            println!("📋 Total addresses: {}", count);
            println!("   ✅ Fully configured: {}", total_succeeded);
            if total_failed > 0 {
                println!("   ❌ Failed: {}", total_failed);
            }

            if total_succeeded == count {
                println!("\n✅ All addresses created and registered for mining!");
                println!("   Donation registrations set up (will activate after mining)");
            } else {
                println!("\n⚠️  Some addresses failed to configure. See details above.");
            }
        }

        Commands::AutoMine {
            output_dir,
            network,
            threads,
            timeout,
        } => {
            use std::collections::{HashMap, HashSet};
            
            println!("🚀 Automated Mining Workflow");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("This will:");
            println!("  1. Create a new wallet with first address");
            println!("  2. Register the first address");
            println!("  3. Mine with first address until solution found");
            println!("  4. Rotate to next existing address (if available)");
            println!("  5. Create new address only when all have solutions");
            println!("  6. Restart from first address on new challenge\n");

            // Find cardano-cli
            let cli_paths = vec![
                "cardano-cli",
                "cardano-cli.exe",
                "./bin/cardano-cli",
                "./bin/cardano-cli.exe",
            ];
            
            let mut cardano_cli = None;
            for path in &cli_paths {
                let check = Command::new(path).arg("--version").output();
                if let Ok(output) = check {
                    if output.status.success() {
                        cardano_cli = Some(path.to_string());
                        break;
                    }
                }
            }
            
            let cardano_cli = cardano_cli.context("cardano-cli not found")?;
            info!("Using cardano-cli: {}", cardano_cli);

            // Create output directory
            fs::create_dir_all(&output_dir)?;
            let wallet_json = output_dir.join("wallet.json");
            
            // Define shared stake key paths
            let shared_stake_vkey = output_dir.join("wallet-stake.vkey");
            let shared_stake_skey = output_dir.join("wallet-stake.skey");
            
            // Load existing wallet or create new one
            let mut wallet = if wallet_json.exists() {
                println!("📂 Loading existing wallet from: {}", wallet_json.display());
                WalletConfig::from_file(&wallet_json)?
            } else {
                println!("📝 Creating new wallet");
                WalletConfig {
                    addresses: Vec::new(),
                    challenge_submissions: HashMap::new(),
                }
            };
            
            // Create shared stake key if it doesn't exist
            if !shared_stake_skey.exists() {
                println!("🔑 Creating shared stake key for wallet...");
                Command::new(&cardano_cli)
                    .args(&[
                        "stake-address", "key-gen",
                        "--verification-key-file", shared_stake_vkey.to_str().unwrap(),
                        "--signing-key-file", shared_stake_skey.to_str().unwrap(),
                    ])
                    .output()?;
                println!("   ✅ Shared stake key created");
            } else {
                println!("🔑 Using existing shared stake key");
            }
            
            let client = api::ScavengerClient::new()?;
            let mut address_counter = wallet.addresses.len();
            
            // Use the wallet's persisted challenge submissions tracker
            // This allows resuming from where we left off after restarts
            let mut current_address_index = 0;
            
            // Create and register the first address only if wallet is empty
            if wallet.addresses.is_empty() {
                let name = format!("addr-{}", address_counter);
                println!("\n📝 Creating initial address: {}", name);

                let payment_vkey = output_dir.join(format!("{}.vkey", name));
                let payment_skey = output_dir.join(format!("{}.skey", name));
                let payment_addr = output_dir.join(format!("{}.addr", name));

                // Generate payment keys only (reuse shared stake key)
                Command::new(&cardano_cli)
                    .args(&[
                        "address", "key-gen",
                        "--verification-key-file", payment_vkey.to_str().unwrap(),
                        "--signing-key-file", payment_skey.to_str().unwrap(),
                    ])
                    .output()?;

                // Build address using shared stake key
                let mut args = vec![
                    "address", "build",
                    "--payment-verification-key-file", payment_vkey.to_str().unwrap(),
                    "--stake-verification-key-file", shared_stake_vkey.to_str().unwrap(),
                ];
                
                if network == "mainnet" {
                    args.push("--mainnet");
                } else {
                    args.push("--testnet-magic");
                    args.push("1");
                }

                let addr_output = Command::new(&cardano_cli).args(&args).output()?;
                let address = String::from_utf8(addr_output.stdout)?.trim().to_string();
                fs::write(&payment_addr, &address)?;

                // Get public key
                let vkey_content = fs::read_to_string(&payment_vkey)?;
                let vkey_json: serde_json::Value = serde_json::from_str(&vkey_content)?;
                let pubkey_hex = vkey_json["cborHex"]
                    .as_str()
                    .context("Failed to extract public key")?
                    .trim_start_matches("5820")
                    .to_string();

                // Add to wallet
                wallet.addresses.push(wallet::AddressEntry {
                    address: address.clone(),
                    verification_key: pubkey_hex.clone(),
                });
                wallet.to_file(&wallet_json)?;

                println!("   ✅ Created: {}", address);

                // Register the new address with retry logic
                println!("🔐 Registering address...");
                
                let mut registered = false;
                let mut attempt = 0;
                
                while !registered && attempt < 10 {
                    attempt += 1;
                    
                    // Fetch T&C with retry
                    let tandc = match client.get_terms_and_conditions(None).await {
                        Ok(tc) => tc,
                        Err(e) => {
                            let err_msg = e.to_string();
                            if err_msg.contains("timeout") || err_msg.contains("timed out") {
                                println!("   ⏳ Network timeout fetching T&C, retrying in 5 seconds... (attempt {})", attempt);
                                tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                                continue;
                            } else {
                                anyhow::bail!("Failed to fetch T&C: {}", e);
                            }
                        }
                    };
                    
                    let signature = wallet::sign_message_with_key(&tandc.message, &address, &payment_skey)?;
                    
                    match client.register(&address, &signature, &pubkey_hex).await {
                        Ok(_) => {
                            println!("   ✅ Registered successfully");
                            registered = true;
                        }
                        Err(e) => {
                            let err_msg = e.to_string();
                            if err_msg.contains("timeout") || err_msg.contains("timed out") {
                                println!("   ⏳ Network timeout during registration, retrying in 5 seconds... (attempt {})", attempt);
                                tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                            } else if err_msg.contains("Too Many Requests") || err_msg.contains("429") {
                                let wait_time = std::cmp::min(10 * attempt, 60);
                                println!("   ⏳ Rate limited, waiting {} seconds... (attempt {})", wait_time, attempt);
                                tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                            } else {
                                anyhow::bail!("Failed to register initial address: {}", e);
                            }
                        }
                    }
                }
                
                if !registered {
                    anyhow::bail!("Failed to register initial address after {} attempts", attempt);
                }

                address_counter += 1;
            } else {
                println!("   ✅ Loaded {} existing address(es)", wallet.addresses.len());
            }

            println!("\n🎯 Starting automated mining loop...\n");

            // Main mining loop
            let start_time = std::time::Instant::now();
            let timeout_duration = std::time::Duration::from_secs(timeout * 60);
            
            // Create mining engine once (will reuse ROM across addresses)
            let mut mining_engine = miner::MiningEngine::new(threads).with_progress_bar(true);
            let mut current_challenge_id: Option<String> = None;
            
            'mining_loop: loop {
                // Check if we've exceeded the challenge timeout
                if start_time.elapsed() >= timeout_duration {
                    println!("\n⏰ Challenge timeout reached. Exiting...");
                    break 'mining_loop;
                }

                // Get current challenge with retry logic
                let challenge_response = loop {
                    match client.get_challenge().await {
                        Ok(response) => break response,
                        Err(e) => {
                            println!("   ⚠️  Failed to fetch challenge: {}", e);
                            println!("   🔄 Retrying in 10 seconds...");
                            tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
                            continue;
                        }
                    }
                };
                
                match challenge_response.data {
                    api::ChallengeData::Before { starts_at } => {
                        println!("⏳ Mining hasn't started yet. Starts at: {}", starts_at);
                        tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
                        continue 'mining_loop;
                    }
                    api::ChallengeData::After => {
                        println!("\n🏁 Mining period has ended");
                        break 'mining_loop;
                    }
                    api::ChallengeData::Active {
                        challenge,
                        next_challenge_starts_at,
                        current_day,
                        max_day,
                        ..
                    } => {
                        // Get or create the submissions set for this challenge
                        let challenge_id = challenge.challenge_id.clone();
                        wallet.challenge_submissions.entry(challenge_id.clone()).or_insert_with(HashSet::new);
                        
                        // Check if current address already submitted for this challenge
                        if wallet.challenge_submissions[&challenge_id].contains(&current_address_index) {
                            // Move to next address
                            current_address_index = (current_address_index + 1) % wallet.addresses.len();
                            
                            // Check if all addresses have submitted for this challenge
                            if wallet.challenge_submissions[&challenge_id].len() >= wallet.addresses.len() {
                                // All addresses used, create a new one
                                // Note: We don't check the countdown timer because challenges don't 
                                // transition exactly at 0:00 - they can start late. Better to keep mining!
                                println!("\n🔄 All addresses have solutions. Creating new address...");
                                
                                // Create and register new address
                                    let name = format!("addr-{}", address_counter);
                                    println!("\n📝 Creating address: {}", name);

                                    let payment_vkey = output_dir.join(format!("{}.vkey", name));
                                    let payment_skey = output_dir.join(format!("{}.skey", name));
                                    let payment_addr = output_dir.join(format!("{}.addr", name));

                                    // Generate payment keys only (reuse shared stake key)
                                    Command::new(&cardano_cli)
                                        .args(&[
                                            "address", "key-gen",
                                            "--verification-key-file", payment_vkey.to_str().unwrap(),
                                            "--signing-key-file", payment_skey.to_str().unwrap(),
                                        ])
                                        .output()?;

                                    // Build address using shared stake key
                                    let mut args = vec![
                                        "address", "build",
                                        "--payment-verification-key-file", payment_vkey.to_str().unwrap(),
                                        "--stake-verification-key-file", shared_stake_vkey.to_str().unwrap(),
                                    ];
                                    
                                    if network == "mainnet" {
                                        args.push("--mainnet");
                                    } else {
                                        args.push("--testnet-magic");
                                        args.push("1");
                                    }

                                    let addr_output = Command::new(&cardano_cli).args(&args).output()?;
                                    let address = String::from_utf8(addr_output.stdout)?.trim().to_string();
                                    fs::write(&payment_addr, &address)?;

                                    // Get public key
                                    let vkey_content = fs::read_to_string(&payment_vkey)?;
                                    let vkey_json: serde_json::Value = serde_json::from_str(&vkey_content)?;
                                    let pubkey_hex = vkey_json["cborHex"]
                                        .as_str()
                                        .context("Failed to extract public key")?
                                        .trim_start_matches("5820")
                                        .to_string();

                                    // Add to wallet
                                    wallet.addresses.push(wallet::AddressEntry {
                                        address: address.clone(),
                                        verification_key: pubkey_hex.clone(),
                                    });
                                    wallet.to_file(&wallet_json)?;

                                    println!("   ✅ Created: {}", address);

                                    // Register the new address with retry logic
                                    println!("🔐 Registering address...");
                                    
                                    let mut registered = false;
                                    let mut attempt = 0;
                                    
                                    while !registered {
                                        attempt += 1;
                                        
                                        // Fetch T&C with retry logic
                                        let tandc = loop {
                                            match client.get_terms_and_conditions(None).await {
                                                Ok(tc) => break tc,
                                                Err(e) => {
                                                    let err_msg = e.to_string();
                                                    if err_msg.contains("timeout") || err_msg.contains("timed out") {
                                                        let wait_time = std::cmp::min(5 * attempt, 30);
                                                        println!("   ⏳ Network timeout fetching T&C, retrying in {} seconds... (attempt {})", wait_time, attempt);
                                                        tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                                                        if attempt >= 10 {
                                                            println!("   ⚠️  Failed to fetch T&C after {} attempts, skipping registration for now", attempt);
                                                            continue 'mining_loop;
                                                        }
                                                    } else {
                                                        println!("   ⚠️  T&C fetch error: {}, retrying...", e);
                                                        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                                                    }
                                                }
                                            }
                                        };
                                        
                                        let signature = wallet::sign_message_with_key(&tandc.message, &address, &payment_skey)?;
                                        
                                        match client.register(&address, &signature, &pubkey_hex).await {
                                            Ok(_) => {
                                                println!("   ✅ Registered successfully");
                                                current_address_index = address_counter;
                                                address_counter += 1;
                                                registered = true;
                                            }
                                            Err(e) => {
                                                let err_msg = e.to_string();
                                                if err_msg.contains("Too Many Requests") || err_msg.contains("429") {
                                                    let wait_time = std::cmp::min(10 * attempt, 60); // Cap at 60 seconds
                                                    println!("   ⏳ Rate limited, waiting {} seconds... (attempt {})", wait_time, attempt);
                                                    tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                                                } else if err_msg.contains("timeout") || err_msg.contains("timed out") {
                                                    let wait_time = std::cmp::min(5 * attempt, 30);
                                                    println!("   ⏳ Network timeout during registration, retrying in {} seconds... (attempt {})", wait_time, attempt);
                                                    tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                                                    if attempt >= 10 {
                                                        println!("   ⚠️  Failed to register after {} attempts, skipping for now", attempt);
                                                        continue 'mining_loop;
                                                    }
                                                } else {
                                                    println!("   ⚠️  Registration error: {}, retrying in 10 seconds...", e);
                                                    tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
                                                    if attempt >= 10 {
                                                        println!("   ⚠️  Failed to register after {} attempts, skipping for now", attempt);
                                                        continue 'mining_loop;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            } else {
                                // Skip addresses that already submitted
                                while wallet.challenge_submissions[&challenge_id].contains(&current_address_index) {
                                    current_address_index = (current_address_index + 1) % wallet.addresses.len();
                                }
                                println!("\n🔄 Switching to address {}", current_address_index);
                            }
                        }

                        let current_address = &wallet.addresses[current_address_index].address;
                        let difficulty_level = miner::difficulty_to_level(&challenge.difficulty);
                        
                        println!("\n🎯 Day {}/{} - Challenge {}", current_day, max_day, challenge.challenge_id);
                        println!("   Difficulty: {} ({})", challenge.difficulty, difficulty_level);
                        println!("   Mining with address {}: {}", current_address_index, current_address);
                        println!("   Addresses: {} created, {} used this challenge", wallet.addresses.len(), wallet.challenge_submissions[&challenge_id].len());

                        // Initialize ROM only if this is a new challenge (ROM is challenge-specific, not address-specific)
                        if current_challenge_id.as_ref() != Some(&challenge.challenge_id) {
                            println!("🔧 Initializing ROM for challenge {}...", challenge.challenge_id);
                            mining_engine.initialize_rom(&challenge.no_pre_mine)?;
                            current_challenge_id = Some(challenge.challenge_id.clone());
                        } else {
                            println!("♻️  Reusing ROM from previous address (same challenge)");
                        }
                        
                        println!("\n⛏️  Mining...");
                        let remaining_time = timeout_duration.saturating_sub(start_time.elapsed());
                        let mining_result = mining_engine.mine(
                            &challenge,
                            current_address,
                            Some(remaining_time),
                        )?;

                        match mining_result {
                            miner::MiningResult::Solution(nonce) => {
                                println!("\n🎉 Solution found!");
                                println!("   Nonce: {}", nonce);

                                // Submit solution (convert nonce to 16-char hex string without 0x prefix)
                                let nonce_hex = format!("{:016x}", nonce);
                                println!("📤 Submitting solution...");
                                
                                // Retry submission up to 5 times with exponential backoff
                                let mut submission_result = None;
                                for submit_attempt in 1..=5 {
                                    match client.submit_solution(
                                        current_address,
                                        &challenge.challenge_id,
                                        &nonce_hex,
                                    ).await {
                                        Ok(response) => {
                                            submission_result = Some(Ok(response));
                                            break;
                                        }
                                        Err(e) => {
                                            let err_msg = e.to_string();
                                            // Retry on network errors (timeouts, connection errors, service unavailable)
                                            let is_retryable = err_msg.contains("timed out") 
                                                || err_msg.contains("timeout")
                                                || err_msg.contains("connection error")
                                                || err_msg.contains("forcibly closed")
                                                || err_msg.contains("unavailable")
                                                || err_msg.contains("service unavailable")
                                                || err_msg.contains("INTERNAL_FUNCTION_SERVICE_UNAVAILABLE");
                                            
                                            if is_retryable && submit_attempt < 5 {
                                                let wait_time = 2_u64.pow(submit_attempt) * 5; // 10, 20, 40, 80 seconds
                                                println!("   ⚠️  Network error during submission (attempt {}/5): {}", submit_attempt, err_msg.lines().next().unwrap_or(&err_msg));
                                                println!("   🔄 Retrying in {} seconds...", wait_time);
                                                tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                                            } else {
                                                submission_result = Some(Err(e));
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                match submission_result.unwrap() {
                                    Ok(response) => {
                                        println!("   ✅ Solution accepted!");
                                        println!("   Receipt timestamp: {}", response.crypto_receipt.timestamp);
                                        
                                        // Mark this address as having submitted for this challenge
                                        wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                        
                                        // Save wallet to persist submission tracking
                                        wallet.to_file(&wallet_json)?;
                                        
                                        println!("   Progress: {}/{} addresses used", wallet.challenge_submissions[&challenge_id].len(), wallet.addresses.len());

                                        // Brief pause before continuing
                                        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                                    }
                                    Err(e) => {
                                        let err_msg = e.to_string();
                                        if err_msg.contains("Address is not registered") {
                                            println!("   ⚠️  Address not registered. Attempting to register now...");
                                            
                                            // Try to register this address
                                            let addr_name = format!("addr-{}", current_address_index);
                                            let payment_skey = output_dir.join(format!("{}.skey", addr_name));
                                            
                                            if payment_skey.exists() {
                                                // Get T&C with retry logic
                                                let tandc = loop {
                                                    match client.get_terms_and_conditions(None).await {
                                                        Ok(tc) => break tc,
                                                        Err(e) => {
                                                            println!("   ⚠️  Failed to fetch T&C: {}", e);
                                                            println!("   🔄 Retrying in 5 seconds...");
                                                            tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                                                        }
                                                    }
                                                };
                                                let signature = match wallet::sign_message_with_key(&tandc.message, current_address, &payment_skey) {
                                                    Ok(sig) => sig,
                                                    Err(e) => {
                                                        println!("   ❌ Failed to sign message: {}", e);
                                                        println!("   Marking address as used to skip it.");
                                                        wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                                        wallet.to_file(&wallet_json)?;
                                                        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                                                        continue 'mining_loop;
                                                    }
                                                };
                                                let pubkey = &wallet.addresses[current_address_index].verification_key;
                                                
                                                let mut registered = false;
                                                let mut attempt = 0;
                                                
                                                while !registered && attempt < 5 {
                                                    attempt += 1;
                                                    match client.register(current_address, &signature, pubkey).await {
                                                        Ok(_) => {
                                                            println!("   ✅ Successfully registered address");
                                                            registered = true;
                                                            // Retry submission
                                                            println!("   🔄 Retrying submission...");
                                                            tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                                                            continue 'mining_loop;
                                                        }
                                                        Err(reg_err) => {
                                                            let reg_err_msg = reg_err.to_string();
                                                            if reg_err_msg.contains("Too Many Requests") || reg_err_msg.contains("429") {
                                                                let wait_time = std::cmp::min(10 * attempt, 60);
                                                                println!("   ⏳ Rate limited, waiting {} seconds... (attempt {})", wait_time, attempt);
                                                                tokio::time::sleep(tokio::time::Duration::from_secs(wait_time)).await;
                                                            } else {
                                                                println!("   ❌ Registration failed: {}", reg_err);
                                                                break;
                                                            }
                                                        }
                                                    }
                                                }
                                                
                                                if !registered {
                                                    println!("   ⚠️  Could not register address. Marking as used to skip it.");
                                                    wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                                    wallet.to_file(&wallet_json)?;
                                                }
                                            } else {
                                                println!("   ⚠️  Signing key not found. Marking address as used to skip it.");
                                                wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                                wallet.to_file(&wallet_json)?;
                                            }
                                        } else if err_msg.contains("Solution already exists") {
                                            println!("   ⚠️  Solution was already submitted by someone else");
                                            println!("   Marking address as used and continuing to next address...");
                                            wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                            wallet.to_file(&wallet_json)?;
                                        } else {
                                            println!("   ❌ Submission failed: {}", e);
                                            println!("   Marking address as used and continuing...");
                                            wallet.challenge_submissions.get_mut(&challenge_id).unwrap().insert(current_address_index);
                                            wallet.to_file(&wallet_json)?;
                                        }
                                        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                                    }
                                }
                            }
                            miner::MiningResult::Timeout => {
                                println!("\n⏰ Mining timeout reached");
                                break 'mining_loop;
                            }
                            miner::MiningResult::Stopped => {
                                println!("\n⏸️  Mining stopped");
                                break 'mining_loop;
                            }
                        }
                    }
                }
            }

            println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("📊 Automated Mining Complete");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("📁 Wallet: {}", wallet_json.display());
            println!("📋 Total addresses created: {}", wallet.addresses.len());
            
            let total_solutions: usize = wallet.challenge_submissions.values().map(|s| s.len()).sum();
            println!("✅ Total solutions submitted: {}", total_solutions);
            println!("📅 Challenges participated: {}", wallet.challenge_submissions.len());
            
            println!("\n💡 You can continue mining with:");
            println!("   night-miner --wallet {} mine", wallet_json.display());
        }
    }

    Ok(())
}

fn init_logging(log_level: &str) -> Result<()> {
    let filter = tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| {
        tracing_subscriber::EnvFilter::new(format!("night_miner={},ashmaize=info", log_level))
    });

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer())
        .init();

    Ok(())
}
