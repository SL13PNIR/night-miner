use night_miner::api::client::ScavengerClient;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let wallet_address = "YOUR_WALLET_ADDRESS_HERE";

    println!("Checking if wallet is registered: {}", wallet_address);

    let client = ScavengerClient::new();

    // Try to fetch challenge - this will only work if wallet is registered
    match client.fetch_challenge(wallet_address).await {
        Ok(challenge) => {
            println!("\n✅ Wallet IS registered!");
            println!("Challenge ID: {}", challenge.challenge_id);
            println!("Difficulty: {}", challenge.difficulty);
            println!("no_pre_mine: {}", challenge.no_pre_mine);
            println!("no_pre_mine_hour: {}", challenge.no_pre_mine_hour);
            println!("latest_submission: {}", challenge.latest_submission);
        }
        Err(e) => {
            println!("\n❌ Wallet is NOT registered or error occurred:");
            println!("{:?}", e);
        }
    }

    Ok(())
}
