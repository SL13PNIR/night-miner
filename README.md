# NIGHT Token Miner

High-performance automated miner for the NIGHT Token Scavenger Mine program with smart challenge selection and tamper-resistant developer payment tracking.

**⚠️ Notice**: This software is provided as-is. Use at your own risk. To use this miner, you must agree to the terms and conditions displayed.

## Features

### Smart Mining (v0.3.0+)
- **Smart Challenge Selection** - Automatically mines the easiest available challenge first
- **Optimized Strategy** - Sorts challenges by difficulty, skips expiring challenges
- **10% Developer Payment Cap** - Fair contribution system
- **Enhanced Reliability** - Intelligent retry logic with exponential backoff
- **Advanced Debugging** - Built-in logging system for monitoring and troubleshooting

### Automatic Operations
- **Wallet Generation** - Creates and registers addresses automatically
- **Address Rotation** - One solution per address per challenge
- **Progress Tracking** - Saves state for safe restarts

## Installation

**Download the Binary**
- Download `night-miner.zip` from the [releases](https://github.com/SL13PNIR/night-miner/releases/) page
- Extract to a folder where you want to mine
- Windows only (`.exe` file)

## How to Use

### 1. Start Mining

**Easy Way - Double-click:**
- Simply double-click `night-miner.exe` in Windows Explorer
- Uses all CPU cores by default

**Advanced - PowerShell (for custom thread count):**
```powershell
.\night-miner.exe --threads 8
```

**With Debug Logging (see API calls, errors, etc.):**
```powershell
# Windows PowerShell - Show API debug logs
$env:RUST_LOG="night_miner::api=debug,night_miner=info"
.\night-miner.exe --threads 8

# Show ALL debug logs (very verbose)
$env:RUST_LOG="debug"
.\night-miner.exe --threads 8
```

```cmd
# Windows CMD - Show API debug logs
set RUST_LOG=night_miner::api=debug,night_miner=info
night-miner.exe --threads 8
```

### 2. Accept Terms

On first run, you'll see:
- Official NIGHT Token End-User Terms
- Developer Contribution Agreement

Type `agree` to continue or `decline` to exit.

### 3. Mining Starts Automatically

The miner will:
- Find an unused developer address for you (from embedded pool)
- Create wallet addresses as needed
- Register addresses automatically
- Mine continuously
- Rotate addresses when needed (1 solution per address per challenge)

### 4. That's It!

Just leave it running. The miner handles everything automatically.

## Logging and Debugging

### Log Levels

The miner uses the `RUST_LOG` environment variable to control logging output.

**Available Log Levels:**
- `error` - Only critical errors
- `warn` - Warnings and errors
- `info` - Normal operation (default)
- `debug` - Detailed debugging information
- `trace` - Very detailed tracing (not recommended)

### Logging Examples

**Normal Operation (Default):**
```powershell
.\night-miner.exe --threads 8
```
Shows: Wallet loading, challenge detection, solution submissions, mining progress

**API Debug Logging (Recommended for troubleshooting):**
```powershell
# PowerShell
$env:RUST_LOG="night_miner::api=debug,night_miner=info"
.\night-miner.exe --threads 8

# CMD
set RUST_LOG=night_miner::api=debug,night_miner=info
night-miner.exe --threads 8
```
Shows: API requests, HTTP responses, challenge fetching, solution submission details, rate limits, network errors

**Full Debug Logging (Very Verbose):**
```powershell
$env:RUST_LOG="debug"
.\night-miner.exe --threads 8
```
Shows: Everything including hash attempts, preimage construction, ROM initialization, thread operations

**Module-Specific Logging:**
```powershell
# Debug wallet operations only
$env:RUST_LOG="night_miner::wallet=debug,night_miner=info"

# Debug challenge manager
$env:RUST_LOG="night_miner::challenge_manager=debug,night_miner=info"

# Debug solution submissions
$env:RUST_LOG="night_miner::operations::solution_submitter=debug,night_miner=info"

# Multiple modules
$env:RUST_LOG="night_miner::api=debug,night_miner::wallet=debug,night_miner=info"
```

### What You'll See With API Debug Logging

```
2025-11-09T18:31:03.885489Z DEBUG night_miner::api::client: Fetching current challenge from API
2025-11-09T18:31:04.085965Z DEBUG night_miner::api::client: ✓ Challenge retrieved: Day 11, Challenge #19, Difficulty: 000007FF
2025-11-09T18:31:15.234567Z DEBUG night_miner::api::client: Submitting solution for challenge: **D11C19
2025-11-09T18:31:15.567890Z DEBUG night_miner::api::client: Solution accepted for challenge: **D11C19
```

This helps you:
- Verify API connectivity
- See when challenges are fetched
- Monitor solution submission success/failures
- Diagnose rate limiting or network issues
- Troubleshoot registration problems

## Wallet Statistics

### Check Your Mining Progress

The miner includes a **Wallet Stats** utility to check your earnings and mining statistics.

**Run Wallet Stats:**
```powershell
# Check stats for your primary address
python wallet-stats.py

# Or use the compiled executable (if available)
.\wallet-stats.exe
```

**What It Shows:**
- Total solutions submitted
- Estimated NIGHT token earnings
- Solutions per address
- Challenge participation history
- STAR value calculations (when rates are available)

**Requirements:**
- Python 3.7+ (if using `.py` script)
- Your `auto-mine-wallet/wallet.json` file

**Example Output:**
```
📊 Wallet Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Addresses: 25
Total Solutions: 47
Estimated Earnings: 125.5 NIGHT

Address Breakdown:
  [0] addr1qx9axk... - 3 solutions
  [1] addr1q8na43... - 2 solutions
  [2] addr1qycsvy... - 2 solutions
  ...
```

**Note:** Earnings are estimates based on available STAR rates. Final rewards are determined by the Scavenger Mine program.

## Securing Your Addresses

### ⚠️ CRITICAL: Backup Your Wallet

**Your `auto-mine-wallet/` folder contains the keys to claim your rewards!**

If you lose this folder, **you lose access to your rewards permanently**.

### What to Backup

```
auto-mine-wallet/
├── wallet.json           # List of all your addresses
├── wallet-stake.skey     # Shared stake key
├── wallet-stake.vkey     # Shared stake verification key
├── addr-*.skey           # Payment keys (CRITICAL - needed to claim rewards)
├── addr-*.vkey           # Payment verification keys
├── addr-*.addr           # Address files
├── .dev_payment          # Developer payment tracker (tamper-resistant)
├── .priority             # Developer address assignment (legacy, migrated to .dev_payment)
└── .agreement            # Terms agreement record
```

### Backup Schedule

**⚠️ CRITICAL:** The miner creates new addresses ON THE FLY as it mines!

**Your first backup will be nearly empty.** After several challenges (hours), you'll have many addresses.

**Why this matters:**
- Hour 1: You might have 5 addresses
- Hour 10: You might have 30 addresses  

It depends on how successful the miner is in any particular challenge!

**Backup Strategy:**
1. ✅ **Let the miner run for at least 2-4 hours first** (so addresses are created)
2. ✅ **Then do your first backup** (now you have something worth backing up!)
3. ✅ **Backup regularly after that** (if new addresses are created)
4. ✅ **Backup before stopping the miner** (capture all addresses)
5. ✅ **Store backups in a safe location**

**Don't backup immediately!** Wait until the miner has created addresses during actual mining challenges.

### Simple Backup Command

**Windows PowerShell:**
```powershell
Copy-Item -Recurse "auto-mine-wallet" "backup-$(Get-Date -Format 'yyyy-MM-dd-HHmm')"
```

### Claiming Rewards Later

When the claiming period opens, you'll need:
1. The `addr-*.skey` files to sign transactions
2. The `wallet.json` to know which addresses have rewards
3. Import keys into Eternl wallet or use Cardano CLI to claim

**Without these files, you cannot claim your rewards!**

## Mining

### What Happens When You Mine

1. **Smart Challenge Selection** - Miner automatically selects the easiest available challenge
2. **Developer Payment (10% Cap)** - Developer receives solutions to maintain a maximum 10% ratio (1 dev solution per 9 user solutions)
3. **Your Solutions (90%+)** - The vast majority of solutions go to your generated addresses
4. **Automatic Rotation** - Each address submits 1 solution per challenge, then rotates
5. **Continuous Mining** - Runs 24/7, creating new addresses and adapting to new challenges

### Developer Payment System

**Fair 10% Contribution Cap:**
- Developer can never receive more than 10% of your total solutions
- System tracks: `(dev_solutions / total_solutions) ≤ 10%`
- If ratio would exceed 10%, developer payments are delayed until you find more solutions
- **Example**: Pattern is 9 user solutions → 1 dev solution → repeat (maintaining 10% ratio)
- **First Use**: Developer gets paid on first solution when starting fresh, then 10% cap applies

**Tamper-Resistant Tracking:**
- Separate `.dev_payment` tracker file with cryptographic checksums
- Cross-validates with `wallet.json` to detect manipulation
- XOR obfuscation prevents casual file editing
- Automatic migration from older `.priority` payment tracking system

**Transparency:**
- Mining display shows current stats: `Address #1 | This addr: 44 sols | Your total: 5146 | Dev: 2 (0.0%)`
- Status message when dev payment delayed: `Dev payment delayed (ratio: 10.0%)`
- Full statistics available via detailed stats output

### Example Output

```
🔗 Connecting to mining server...
📥 Cached challenge **D11C24 (Day 11, Difficulty: 000007FF)
   ✅ Challenge added to queue (1 available)

🆕 New challenge detected: **D11C24
   💎 Developer payment pending for this challenge
⛏️  Mining: 🎯 DEVELOPER ADDRESS
⠁ [00:09:32] Hashes: 4052000 | Rate: 7121.80 H/s

✅ Solution found! Nonce: 0a00019a6afc1a78
   ✅ Marked developer address as used for challenge **D11C24
📤 Submitting solution...
   ✅ Solution submitted successfully!
   💰 Estimated Current earnings: 11281.250418 NIGHT

🔄 Switching to generated address 0
📋 Challenge **D11C24 | Day 11/21 | ROM cached ✅
⛏️  Mining: Address #1 | This addr: 44 sols | Your total: 5146 | Dev: 2 (0.0%)
  [00:11:49] Hashes: 632000 | Rate: 9230.46 H/s
```

## FAQ

### Can I stop and restart?
Yes! The miner saves its progress. Just restart with the same command.

### How many addresses will be created?
As many as needed. The miner typically creates 30+ addresses over a single challenge period, depending on difficulty and CPU power. With smart challenge selection, you may create addresses faster by targeting easier challenges.

### What about the 10% developer payment?
The developer receives up to 10% of total solutions as fair compensation for this software. This is enforced by tamper-resistant tracking with cryptographic checksums. The ratio is transparently displayed during mining.

### What if I lose the auto-mine-wallet folder?
**You permanently lose access to all rewards.** This is why regular backups are critical!

### How do I claim rewards later?

**Address Consolidation (Preferred Method - Currently Unavailable):**

The Scavenger Mine API has a `donate_to` endpoint that allows you to register a single Cardano address. Once working, all your mined rewards would be consolidated to that address automatically.

- **Status:** Currently broken, waiting for IOHK to fix
- **When fixed:** This miner will be updated to let you register your desired address
- **Benefit:** You won't need the generated `.skey` files to claim rewards

**Manual Claiming (Backup Method):**

If the `donate_to` endpoint isn't fixed, you'll need to manually claim using:
1. The `addr-*.skey` files to sign transactions
2. Import keys into Eternl wallet or use Cardano CLI

**Important:** Keep your `auto-mine-wallet/` backups safe regardless! Even if address consolidation works, you should retain the keys as a safety backup.

## Disclaimer

This software is provided "as is" without warranty. By using this software, you agree to the developer receiving up to 10% of solutions found as fair compensation. This 10% cap is enforced through tamper-resistant tracking. Mining results depend on network conditions, competition, and luck.

---

**Happy Mining! 🌙**
