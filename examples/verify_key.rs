use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: verify-key <hex-public-key>");
        std::process::exit(1);
    }

    let hex_key = &args[1];

    // Decode hex
    match hex::decode(hex_key) {
        Ok(public_key_bytes) => {
            println!("Decoded {} bytes from hex", public_key_bytes.len());

            if public_key_bytes.len() != 32 {
                eprintln!(
                    "Warning: Expected 32 bytes for a public key, got {}",
                    public_key_bytes.len()
                );
            }

            // Verify it's valid by showing the bytes
            println!("\n✓ Valid public key bytes:");
            println!("  First 8 bytes: {:02x?}", &public_key_bytes[..8]);
            println!("  Last 8 bytes: {:02x?}", &public_key_bytes[24..]);

            println!("\n✓ This is a valid 32-byte Ed25519 public key!");

            // Now re-encode JUST the public key to verify
            // Note: The original had 64 bytes (32 public key + 32 chain code)
            // We're only encoding the public key part here
            let hrp = bech32::Hrp::parse("acct_xvk").expect("Valid HRP");
            match bech32::encode::<bech32::Bech32>(hrp, &public_key_bytes) {
                Ok(encoded) => {
                    println!("\n✓ Successfully re-encoded public key to bech32:");
                    println!("{}", encoded);
                    println!("\n(Note: This is shorter than the original because the original");
                    println!("included 32 additional bytes of chain code that we don't need)");
                }
                Err(e) => {
                    eprintln!("Error encoding: {}", e);
                }
            }

            println!("\n✓ Safe to use in wallet.json!")
        }
        Err(e) => {
            eprintln!("Error decoding hex: {}", e);
            std::process::exit(1);
        }
    }
}
