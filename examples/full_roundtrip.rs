use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: full-roundtrip <acct_xvk1...>");
        std::process::exit(1);
    }

    let original = &args[1];

    println!("Original extended key:");
    println!("{}\n", original);

    // Decode
    match bech32::decode(original) {
        Ok((hrp, data)) => {
            println!("Decoded successfully:");
            println!("  HRP: {}", hrp);
            println!("  Data length: {} bytes", data.len());
            println!("  Data as hex: {}\n", hex::encode(&data));

            // Re-encode with the EXACT same data
            match bech32::encode::<bech32::Bech32>(hrp, &data) {
                Ok(re_encoded) => {
                    println!("Re-encoded:");
                    println!("{}\n", re_encoded);

                    // Compare
                    if original == &re_encoded {
                        println!("✅ PERFECT MATCH! The encoding/decoding is 100% correct!");
                    } else {
                        println!("❌ Mismatch detected");
                        println!("Original:   {}", original);
                        println!("Re-encoded: {}", re_encoded);
                    }
                }
                Err(e) => {
                    eprintln!("Error re-encoding: {}", e);
                }
            }
        }
        Err(e) => {
            eprintln!("Error decoding: {}", e);
        }
    }
}
