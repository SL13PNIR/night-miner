**⚠️ Notice**: This repository is provided as-is for informational purposes during the 30-day NIGHT Token Scavenger Mine event. Issues and pull requests are disabled. No support or updates will be provided. Use at your own risk.

# NIGHT Token Miner

High-performance Rust miner for the NIGHT Token Scavenger Mine program.

## Quick Start

### Prerequisites

**Required:**
- **Rust toolchain** (1.70+): Install from https://rustup.rs/
- **Internet connection**: For API communication with Scavenger Mine service

**Optional (for AutoMine address creation):**
- **Cardano CLI**: Only needed if using AutoMine to create new addresses
  - Windows: Download from https://github.com/IntersectMBO/cardano-node/releases
  - Linux: `sudo apt install cardano-cli`
  - macOS: `brew install cardano-cli`
  - Or place `cardano-cli.exe` in `./bin/` directory

**Optional (for manual mining):**
- **Cardano wallet** (Eternl, Nami, etc.) for signing registration messages

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

   **Dependencies handled automatically:**
   - **AshMaize library**: Automatically fetched from GitHub during build (`ashmaize = { git = "https://github.com/input-output-hk/ce-ashmaize", branch = "master" }`)
   - All Rust crates downloaded from crates.io
   - No manual dependency installation needed

> **Note**: On Windows, use `.\target\release\night-miner.exe` to run commands. Examples below use Linux/Mac syntax (`./target/release/night-miner`) for brevity.

## Registration

**Note:** If you use **AutoMine** (recommended), registration is handled automatically! You can skip this section.

For **manual mining only**, you must register your Cardano wallet address before mining.

### Manual Registration (For Manual Mining Mode)

#### Step 1: Get Terms and Conditions

```bash
./target/release/night-miner tandc
```

This displays the message you need to sign.

#### Step 2: Sign the Message

1. Open your Cardano wallet (Eternl, Nami, etc.)
2. Go to the "Sign message" or "CIP-30 Sign" feature
3. Paste the entire T&C message
4. Sign it
5. Copy the resulting signature (long hex string starting with `8458...`)

#### Step 3: Register

```bash
./target/release/night-miner --wallet wallet.json register -s YOUR_SIGNATURE_HERE
```

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

### Wallet Structure and File Organization

AutoMine creates an `auto-mine-wallet/` directory containing all wallet files:

```
auto-mine-wallet/
├── wallet.json              # Main wallet configuration
├── wallet-stake.skey        # Shared stake signing key
├── wallet-stake.vkey        # Shared stake verification key
├── addr-0.skey             # Payment signing key for address 0
├── addr-0.vkey             # Payment verification key for address 0
├── addr-0.addr             # Address file for address 0
├── addr-1.skey             # Payment signing key for address 1
├── addr-1.vkey             # Payment verification key for address 1
├── addr-1.addr             # Address file for address 1
└── ... (one set of files per address created)
```

**wallet.json structure:**

```json
{
  "addresses": [
    {
      "address": "addr1qx...",
      "verification_key": "cad3a195..."
    },
    {
      "address": "addr1qy...",
      "verification_key": "7be1a98f..."
    }
  ],
  "challenge_submissions": {
    "**D02C22": [0, 1, 2, 3, 4],
    "**D02C23": [0, 1, 2]
  }
}
```

- **addresses**: Array of all wallet addresses with their verification keys (100+ addresses typical)
- **challenge_submissions**: Tracks which address indices have submitted for each challenge (persists across restarts)
- All addresses share a single stake key for proper Cardano wallet structure
- Each address gets its own payment key pair (.skey/.vkey files)

**How the 1-solution-per-address limit works:**
1. Challenge **D02C23 starts
2. Miner tries address 0 → finds solution → submits → marks address 0 as used
3. Miner switches to address 1 → finds solution → submits → marks address 1 as used
4. Continues through all addresses until challenge ends
5. When **D02C24 starts, ALL addresses reset and can be reused
6. Process repeats for every new challenge

### Important: Claiming Your Rewards

**Current Limitation (November 2025):**

The `donate_to` API endpoint is currently **broken** on the Scavenger Mine service. This affects reward consolidation:

- ❌ **Cannot currently consolidate** solutions from multiple addresses to a single address
- ⚠️ **You will need to claim rewards on EACH address individually** when claiming opens
- 📁 **Keep your `auto-mine-wallet/` directory safe** - you'll need all the `.skey` files to claim

**Once donate_to is fixed:**

When the API is working again, you'll be able to:
- ✅ Use the `donate` command to consolidate solutions to a single address
- ✅ Claim all rewards from one address instead of many
- ✅ Simplify the claiming process

**Importing Keys to Eternl Wallet:**

You can import your generated addresses into Eternl (or other Cardano wallets) for claiming:

1. **Locate your signing key files** in `auto-mine-wallet/`:
   - `addr-0.skey`, `addr-1.skey`, etc. (payment keys)
   - `wallet-stake.skey` (stake key - shared by all addresses)

2. **Import into Eternl:**
   - Open Eternl → Add Wallet → Restore Wallet
   - Choose "Import Keys" or "24-word phrase" (depending on Eternl version)
   - For direct key import, you may need to convert the `.skey` files
   - All addresses share the same stake key, so they belong to the same wallet

3. **Alternative - Use Cardano CLI:**
   ```bash
   # View your addresses
   cat auto-mine-wallet/addr-0.addr
   cat auto-mine-wallet/addr-1.addr
   
   # Sign transactions with the keys when claiming opens
   cardano-cli transaction sign \
     --signing-key-file auto-mine-wallet/addr-0.skey \
     --tx-body-file tx.raw \
     --out-file tx.signed
   ```

**Backup Strategy:** 

⚠️ **CRITICAL: Backup your `auto-mine-wallet/` directory REGULARLY!**

**Important:** New addresses are created on-the-fly as mining progresses:
- AutoMine creates new addresses automatically when all current addresses have submitted solutions
- Each new address generates 3 new files: `.skey`, `.vkey`, and `.addr`
- The `wallet.json` file is also updated continuously

**Recommended backup schedule:**
1. **Initial backup**: Immediately after starting AutoMine for the first time
2. **Periodic backups**: Every few hours while mining is active
3. **Daily backups**: At minimum, backup once per day
4. **After restarts**: Backup after stopping and restarting the miner

**What to backup:**
- ✅ Entire `auto-mine-wallet/` directory (100+ files after extended mining)
- ✅ `wallet.json` (tracks all addresses and submissions)
- ✅ `wallet-stake.skey` and `wallet-stake.vkey` (shared stake keys)
- ✅ All `addr-*.skey` files (payment signing keys - needed to claim rewards)

**Why incremental backups matter:**
- If you lose the `.skey` files, you **permanently lose access** to those addresses' rewards
- A backup from Day 1 won't include addresses created on Days 2-21
- You need the most recent backup to claim rewards from ALL addresses
- Store backups securely in multiple locations (external drive, cloud storage, etc.)

**Simple backup command:**
```bash
# Windows PowerShell
Copy-Item -Recurse "auto-mine-wallet" "auto-mine-wallet-backup-$(Get-Date -Format 'yyyy-MM-dd-HHmm')"

# Linux/Mac
cp -r auto-mine-wallet "auto-mine-wallet-backup-$(date +%Y-%m-%d-%H%M)"
```

## Mining

### AutoMine (Recommended) 🚀

The **AutoMine** feature is the easiest and most efficient way to mine. It automatically:
- Creates and manages wallet addresses
- Registers new addresses as needed
- Rotates through addresses for each challenge
- Reuses addresses across multiple challenges
- Tracks which addresses have submitted solutions
- Persists state across restarts
- Maximizes mining efficiency with ROM reuse

**Start AutoMining:**

```bash
# Windows
.\target\release\night-miner.exe auto-mine --threads 16 --timeout 120

# Linux/Mac
./target/release/night-miner auto-mine --threads 16 --timeout 120
```

**Cardano CLI Detection:**

AutoMine automatically searches for `cardano-cli` in these locations:
1. System PATH (global installation)
2. `./bin/cardano-cli.exe` (Windows)
3. `./bin/cardano-cli` (Linux/Mac)

If not found, AutoMine will display installation instructions. The CLI is only used for creating new wallet addresses - all mining logic is built-in.

**What AutoMine does:**
1. Creates `auto-mine-wallet/` directory with all wallet files
2. Creates first address and registers it automatically
3. Mines until a solution is found
4. **Rotates to next address** (each address limited to 1 solution per challenge)
5. Creates new addresses automatically as needed
6. When a new challenge starts, **reuses all existing addresses** from the beginning
7. Continues indefinitely, maximizing solutions per challenge

**Why multiple addresses?**

The Scavenger Mine limits each address to **1 solution per challenge**. To maximize earnings:
- AutoMine creates many addresses (100+ is common)
- Each address can submit 1 solution per challenge
- With ~24 challenges per day, you can earn 100+ solutions daily
- All addresses belong to the same wallet (shared stake key)

**Benefits:**
- **180× faster than browser mining** (~3 solutions/minute vs browser's 24/day)
- Fully automated - creates and manages 100+ addresses automatically
- Persistent state - resume mining after restart
- Efficient ROM reuse across all addresses
- No time wasted on manual registration
- All addresses stored in `auto-mine-wallet/` directory

### Manual Mining (Single Address)

If you prefer to mine with a single address or have pre-registered addresses, you can use the manual mining command:

```bash
./target/release/night-miner --wallet wallet.json --threads 8 mine
```

**When to use manual mode:**
- You have a pre-existing wallet setup
- You want to mine with a single specific address
- You prefer manual control over the process

**Limitations vs AutoMine:**
- **Limited to 1 solution per challenge** (only uses primary address)
- No automatic address creation or rotation
- No persistent challenge tracking
- Must manually register addresses beforehand
- Less efficient for maximizing earnings (AutoMine can submit 100+ solutions per challenge)

### Command Options

**AutoMine:**
- `--output-dir <DIR>`: Wallet directory (default: `auto-mine-wallet`)
- `--threads <N>`: Number of mining threads (default: CPU count)
- `--timeout <MINUTES>`: Challenge timeout in minutes (default: 55)
- `--network <mainnet|testnet>`: Network (default: `mainnet`)

**Manual Mining:**
- `--wallet <FILE>`: Path to your wallet configuration file (default: `wallet.json`)
- `--threads <N>`: Number of mining threads (default: CPU count)
- `--log-level <LEVEL>`: Logging verbosity: `trace`, `debug`, `info`, `warn`, `error` (default: `info`)

### Example AutoMine Output

```
🚀 Automated Mining Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Loading existing wallet from: auto-mine-wallet\wallet.json
   ✅ Loaded 113 existing address(es)
🔑 Using existing shared stake key

🎯 Starting automated mining loop...

🎯 Day 2/21 - Challenge **D02C23
   Difficulty: 0001FFFF (Extreme)
   Mining with address 37: addr1qy...
   Addresses: 113 created, 82 used this challenge
♻️ Reusing ROM from previous challenge

⛏️  Mining...
   ✅ Solution found! Nonce: 0700003a2c8f1a3b | Time: 4.21s | Rate: 9,847 H/s
   ✅ Solution submitted successfully!

🔄 Switching to address 53
```

## Other Commands

### Check Current Challenge

```bash
./target/release/night-miner challenge
```

Shows the current active challenge and its difficulty.

### View Work Rates

```bash
./target/release/night-miner rates
```

Displays the current work-to-STAR conversion rates.

### Donate/Consolidate Solutions (Currently Broken)

```bash
./target/release/night-miner --wallet wallet.json donate \
  --destination addr1qx... \
  --signature YOUR_SIGNATURE \
  --address addr1qy...
```

**Status:** ⚠️ This command exists but the API endpoint is currently non-functional. Once fixed, you'll be able to consolidate solutions from multiple mining addresses to a single destination address for easier claiming.

## Troubleshooting

### Lost or Missing Addresses

**Problem:** "I backed up my wallet on Day 1, but now I have 100+ addresses and my backup only has 10."

**Solution:** 
- AutoMine creates addresses continuously throughout the mining period
- You need to backup regularly to capture newly created addresses
- Restore the most recent backup to ensure you have all addresses
- Consider setting up automatic/scheduled backups

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

- **Use AutoMine**: The automated workflow is the most efficient way to mine
- **Use all CPU cores**: Set `--threads` to your CPU core count for maximum performance
- **Release build**: Always use `cargo build --release` for 10-20x speed improvement
- **Let it run**: AutoMine handles everything - just let it run indefinitely
- **Network resilience**: Built-in retry logic handles network errors automatically
- **Persistent state**: Restart anytime - the miner resumes where it left off

### Performance Stats

With an Intel i9-11900H (8 cores, 16 threads):
- **Hash rate**: ~9,000-9,500 H/s
- **Solutions**: ~3 per minute
- **Daily output**: ~4,320 solutions/day
- **vs Browser**: **180× faster** than browser mining (24 solutions/day)

## ~~Running Multiple Instances~~

**Not recommended:** AutoMine automatically manages multiple addresses within a single instance, which is more efficient than running multiple processes.

Instead, use **AutoMine** which automatically:
- Creates and registers multiple addresses
- Rotates through them efficiently
- Reuses the 1GB ROM across all addresses
- Tracks submissions persistently
- Maximizes solutions without manual management

**Old approach (inefficient):**
- Multiple processes × 1.2GB RAM each = high memory usage
- Multiple ROM initializations per challenge
- Manual address management

**AutoMine approach (efficient):**
- Single process with address rotation
- One ROM reused across all addresses
- Automatic registration and tracking
- Lower memory usage (~1.2GB total)

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
- **ROM Size**: 1 GB (initialized once per challenge, ~1.5s)
- **ROM Reuse**: Shared across all addresses in the same challenge
- **Hash Loops**: 8
- **Instructions**: 256
- **Pre-size**: 16 MB
- **Mixing Numbers**: 4

### Key Optimizations

1. **ROM Reuse**: 1GB ROM is initialized once per challenge and reused across all addresses (saves ~91.5s per address)
2. **Address Rotation**: Automatically switches addresses after finding solutions
3. **Persistent Tracking**: `challenge_submissions` in `wallet.json` tracks which addresses submitted for which challenges
4. **Network Resilience**: Infinite retry loops with exponential backoff for all network operations
5. **Challenge Persistence**: Resumes mining from correct address after restart

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
