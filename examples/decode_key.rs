use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: decode-key <acct_xvk1...>");
        std::process::exit(1);
    }

    let extended_key = &args[1];

    match bech32::decode(extended_key) {
        Ok((hrp, data)) => {
            println!("HRP: {}", hrp);
            println!("Data length: {} bytes", data.len());

            // For account extended keys (acct_xvk1), the structure is:
            // 64 bytes total: 32 bytes public key + 32 bytes chain code
            // We only need the first 32 bytes (the public key)
            if data.len() >= 32 {
                let public_key = &data[..32];
                println!("\nRaw Public Key (64 hex chars):");
                println!("{}", hex::encode(public_key));
            } else {
                eprintln!("Error: Data too short, expected at least 32 bytes");
                std::process::exit(1);
            }
        }
        Err(e) => {
            eprintln!("Error decoding bech32: {}", e);
            std::process::exit(1);
        }
    }
}
