**⚠️ Notice**: This repository is provided as-is for informational purposes during the 30-day NIGHT Token Scavenger Mine event. Issues and pull requests are disabled. No support or updates will be provided. Use at your own risk.

# NIGHT Token Miner

High-performance Rust miner for the NIGHT Token Scavenger Mine program.

## Quick Start

### Prerequisites

- **Rust toolchain** (1.70+): Install from https://rustup.rs/
- **Cardano wallet** (Eternl, Nami, etc.) with a registered address
- **Windows, Linux, or macOS**

### Installation

1. **Clone or download this project**
   ```bash
   cd night-miner
   ```

2. **Build the miner**
   ```bash
   cargo build --release
   ```
   
   The compiled binary will be at:
   - **Windows**: `target\release\night-miner.exe`
   - **Linux/Mac**: `target/release/night-miner`

> **Note**: On Windows, use `.\target\release\night-miner.exe` to run commands. Examples below use Linux/Mac syntax (`./target/release/night-miner`) for brevity.

## Registration

Before you can mine, you must register your Cardano wallet address.

### Step 1: Get Terms and Conditions

```bash
./target/release/night-miner tandc
```

This displays the message you need to sign. Look for the line starting with:
```
I agree to abide by the terms and conditions...
```

### Step 2: Sign the Message

1. Open your Cardano wallet (Eternl, Nami, etc.)
2. Go to the "Sign message" or "CIP-30 Sign" feature
3. Paste the entire T&C message
4. Sign it
5. Copy the resulting signature (long hex string starting with `8458...`)

### Step 3: Register

```bash
./target/release/night-miner --wallet wallet.json register -s YOUR_SIGNATURE_HERE
```

Replace `YOUR_SIGNATURE_HERE` with the signature from Step 2.

You should see:
```
Successfully registered address: addr1q...
Receipt timestamp: 2025-10-30 13:01:17.983 UTC
```

## Configuration

Create a `wallet.json` file with your Cardano address:

```json
{
  "address": "addr1qx...",
  "signing_key": "NOT_USED_EXTERNALLY_SIGNED",
  "verification_key": "YOUR_VERIFICATION_KEY_HERE"
}
```

**Note:** The `signing_key` field is not used since we sign externally with your wallet. The `verification_key` is your wallet's public key.

## Mining

Once registered, start mining:

```bash
./target/release/night-miner --wallet wallet.json --threads 8 mine
```

### Command Options

- `--wallet <FILE>`: Path to your wallet configuration file (default: `wallet.json`)
- `--threads <N>`: Number of mining threads (default: CPU count)
- `--log-level <LEVEL>`: Logging verbosity: `trace`, `debug`, `info`, `warn`, `error` (default: `info`)

### Example Output

```
2025-10-30T16:18:35Z  INFO  Starting NIGHT Token Miner
2025-10-30T16:18:35Z  INFO  Mining with address: addr1qx...
2025-10-30T16:18:39Z  INFO  Fetched challenge: **D01C17 (Day 1, Challenge 17)
2025-10-30T16:18:39Z  INFO  Day 1/21 - Challenge **D01C17 - Difficulty: 00007FFF
2025-10-30T16:18:41Z  INFO  ROM initialized in 2.71s
2025-10-30T16:18:41Z  INFO  Starting mining for challenge **D01C17
2025-10-30T16:18:44Z  INFO  Solution found! Nonce: 0400019a35ea1088 | Time: 3.01s
2025-10-30T16:18:44Z  INFO  Solution submitted successfully!
```

## Other Commands

### Check Current Challenge

```bash
./target/release/night-miner --wallet wallet.json challenge
```

Shows the current active challenge and its difficulty.

### View Work Rates

```bash
./target/release/night-miner rates
```

Displays the current work-to-STAR conversion rates.

## Troubleshooting

### "Solution already exists"

This means your solution was valid but another miner found the same nonce first. This is normal - just keep mining!

### "Solution does not meet difficulty"

**This should not happen after our fixes.** If you see this, there may be an issue. Check:
1. Your wallet is properly registered
2. You're using the latest build
3. The challenge hasn't expired

### "Failed to fetch challenge"

Check your internet connection and ensure the API is accessible:
```bash
curl https://scavenger.prod.gd.midnighttge.io/health
```

### Build Errors

If you get compilation errors:
```bash
cargo clean
cargo build --release
```

### API Rate Limiting

The miner automatically handles challenge fetching and submission. Each challenge lasts 1 hour. The miner will:
1. Fetch the current challenge
2. Mine solutions until the challenge ends
3. Wait for the next challenge
4. Repeat

## Performance Tips

- **Use all CPU cores**: Set `--threads` to your CPU core count for maximum performance
- **Release build**: Always use `cargo build --release` for 10-20x speed improvement
- **Background mining**: On Windows, you can run in a minimized PowerShell window
- **Multiple wallets**: Run multiple instances with different wallets to increase chances

## Running Multiple Instances

You can run multiple miner instances simultaneously with different wallet addresses to increase your chances of finding solutions.

### Setup

1. **Create separate wallet files** for each address:
   ```bash
   cp wallet.json wallet1.json
   cp wallet.json wallet2.json
   # Edit each file with different addresses
   ```

2. **Register each wallet** (if not already registered):
   ```bash
   ./target/release/night-miner --wallet wallet1.json register -s SIGNATURE_1
   ./target/release/night-miner --wallet wallet2.json register -s SIGNATURE_2
   ```

### Running

**Option 1: Separate Terminal Windows**

Open multiple terminal windows and run one instance in each:

```bash
# Terminal 1
./target/release/night-miner --wallet wallet1.json --threads 4 mine

# Terminal 2
./target/release/night-miner --wallet wallet2.json --threads 4 mine
```

**Option 2: Background Processes (Linux/Mac)**

```bash
# Start instances in background
./target/release/night-miner --wallet wallet1.json --threads 4 mine > miner1.log 2>&1 &
./target/release/night-miner --wallet wallet2.json --threads 4 mine > miner2.log 2>&1 &

# Monitor logs
tail -f miner1.log
tail -f miner2.log

# View all running miners
ps aux | grep night-miner

# Stop all miners
pkill night-miner
```

**Option 3: Background Jobs (Windows PowerShell)**

```powershell
# Start instances as background jobs
Start-Job -ScriptBlock { & ".\target\release\night-miner.exe" --wallet wallet1.json --threads 4 mine }
Start-Job -ScriptBlock { & ".\target\release\night-miner.exe" --wallet wallet2.json --threads 4 mine }

# View running jobs
Get-Job

# View job output
Receive-Job -Id 1 -Keep
Receive-Job -Id 2 -Keep

# Stop all jobs
Get-Job | Stop-Job
Get-Job | Remove-Job
```

### Thread Allocation

When running multiple instances, divide your CPU cores:
- **8-core CPU**: 2 instances × 4 threads each
- **16-core CPU**: 4 instances × 4 threads each, or 2 instances × 8 threads each
- Leave 1-2 cores free for system tasks

### Important Notes

- Each wallet can only submit **one solution per challenge**
- Multiple instances compete independently
- Monitor CPU and memory usage to avoid system slowdown
- Each instance needs ~1.2GB RAM (for the 1GB AshMaize ROM)

## Project Structure

```
night-miner/
├── src/
│   ├── main.rs              # Entry point
│   ├── api/                 # Scavenger Mine API client
│   ├── miner/               # Mining engine & AshMaize hashing
│   ├── coordinator/         # Mining session management
│   └── wallet/              # Wallet configuration
├── Cargo.toml              # Rust dependencies
├── wallet.json             # Your wallet configuration
└── README.md               # This file
```

## Technical Details

### Mining Algorithm

The miner uses the **AshMaize** proof-of-work algorithm:
- **ROM Size**: 1 GB (initialized once per challenge)
- **Hash Loops**: 8
- **Instructions**: 256
- **Pre-size**: 16 MB
- **Mixing Numbers**: 4

### Preimage Format

Solutions are computed by hashing a preimage constructed as:
```
nonce (16 hex chars) + address + challenge_id + difficulty + no_pre_mine + timestamp + no_pre_mine_hour
```

Example:
```
0012e0239a4a81beaddr1q9e45x...***D01C1600007FFFe8a195...2025-10-31T14:59:59.000Z452810707
```

### Difficulty Check

A solution is valid when:
```
(hash_u32 | difficulty_u32) == difficulty_u32
```

This checks that all bits set in the hash are also set in the difficulty target (hash is a subset of target bits).

## References

- [**Midnight Scavenger Mine API Reference** (October 2025 / Version 1.0)](https://45047878.fs1.hubspotusercontent-na1.net/hubfs/45047878/Midnight%20-%20Whitepaper%20treatment%20for%20Scavenger%20Mine%20API%20V3.pdf)  Midnight TGE Ltd

## Contributing

Since the scavenger mine phase is only 30 days long, I do not intend to provide support or fixes.

## License

This project is open source. The AshMaize algorithm library is licensed under Apache-2.0 / MIT.

## Disclaimer

This software is provided "as is" without warranty. Mining results depend on network conditions, competition, and luck. Always verify transactions and wallet addresses before use.

---

**Happy Mining! 🌙**
