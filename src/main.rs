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

            info!("Mining with address: {}", wallet.get_address());
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

            info!("Registering address: {}", wallet.get_address());

            let response = client
                .register(wallet.get_address(), &signature, wallet.get_pubkey())
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

            info!("Donating from {} to {}", wallet.get_address(), destination);

            let response = client
                .donate_to(&destination, wallet.get_address(), &signature)
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
            // Create a template wallet config
            let wallet = WalletConfig {
                address: "addr1q8upjxynn626c772r5nzym...".to_string(),
                signing_key: "YOUR_PRIVATE_KEY_HEX".to_string(),
                verification_key: "YOUR_PUBLIC_KEY_HEX_64_CHARS".to_string(),
            };

            wallet.to_file(&output)?;
            info!("Created wallet configuration template at: {:?}", output);
            println!("\n⚠️  IMPORTANT: Update the wallet.json file with your actual:");
            println!("  - Cardano address");
            println!("  - Public key (64-character hex format)");
            println!("  - DO NOT put your private key in the file (use external signing)");
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
