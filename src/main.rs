mod api;
mod config;
mod coordinator;
mod miner;
mod wallet;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::PathBuf;
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
        /// Message to sign
        #[arg(short, long)]
        message: String,

        /// Path to signing key file (Cardano .skey format)
        #[arg(short = 'k', long)]
        signing_key: Option<PathBuf>,

        /// Output the signature to stdout instead of pretty format
        #[arg(short = 'o', long)]
        stdout: bool,
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

        Commands::Register { signature } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(wallet_path)?;

            let client = api::ScavengerClient::new()?;

            info!("Registering address: {}", wallet.get_primary_address());

            let response = client
                .register(wallet.get_primary_address(), &signature, wallet.get_primary_pubkey())
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
        } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(wallet_path)?;

            let client = api::ScavengerClient::new()?;

            info!("Donating from {} to {}", wallet.get_primary_address(), destination);

            let response = client
                .donate_to(&destination, wallet.get_primary_address(), &signature)
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
            println!("   1. Get T&C message:");
            println!("      night-miner tandc");
            println!("   2. Sign the T&C message:");
            println!("      night-miner --wallet {} sign --message \"<message>\" --signing-key {}", 
                     wallet_json.display(), payment_skey.display());
            println!("   3. Register with signature:");
            println!("      night-miner --wallet {} register --signature \"<signature>\"", 
                     wallet_json.display());
            println!("   4. Start mining:");
            println!("      night-miner --wallet {} mine", wallet_json.display());
        }

        Commands::Sign {
            message,
            signing_key,
            stdout,
        } => {
            let wallet_path = cli.wallet.unwrap_or_else(|| PathBuf::from("wallet.json"));
            let wallet = WalletConfig::from_file(&wallet_path)?;

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

            // Derive the actual address from the signing key to ensure signature matches
            let wallet_dir = wallet_path.parent().unwrap_or_else(|| std::path::Path::new(".")).to_path_buf();
            let address = wallet::derive_address_from_key(&key_path, &wallet_dir)?;
            
            info!("Derived address from signing key: {}", address);

            // Find the matching verification key for this address
            let pubkey = wallet.get_pubkey_for_address(&address)
                .context(format!("Address {} not found in wallet.json", address))?;

            let signature = wallet::sign_message_with_key(&message, &address, &key_path)?;

            if stdout {
                println!("{}", signature);
            } else {
                println!("✅ Signature generated successfully!");
                println!("\nFor address: {}", address);
                println!("With pubkey: {}", pubkey);
                println!("\nSignature:");
                println!("{}", signature);
                println!("\n💡 Use this to register:");
                println!("   night-miner --wallet {} register --signature \"{}\"", 
                         wallet_path.display(), signature);
            }
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
