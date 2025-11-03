# NIGHT Token Miner

High-performance automated miner for the NIGHT Token Scavenger Mine program.

**⚠️ Notice**: This software is provided as-is. Use at your own risk. To use this miner, you must agree to the terms and conditions displayed.

## Installation

**Download the Binary**
- Download `night-miner.zip` from the [releases](https://github.com/SL13PNIR/night-miner/releases/tag/v0.1.0) page
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
├── .priority             # Your assigned developer address (obfuscated)
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

1. **Developer Address** - First solution goes to developer (your compensation for this software)
2. **Your Addresses** - Following solutions go to your generated addresses
3. **Automatic Rotation** - Each address submits 1 solution per challenge, then rotates to next
4. **Continuous Mining** - Miner runs 24/7 creating new addresses as needed

### Example Output

Mining with generated address 0: addr1qywn...
⛏️  Mining...
✅ Solution found! Nonce: 0100019a470bb2e7 | Time: 14.14s
✅ Solution submitted successfully!

## FAQ

### Can I stop and restart?
Yes! The miner saves its progress. Just restart with the same command.

### How many addresses will be created?
As many as needed. The miners can typically create 30+ addresses over a single challenge period, but it depends on difficulty and CPU power.

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

This software is provided "as is" without warranty. By using this software, you agree to mine one solution per challenge for the developer. Mining results depend on network conditions, competition, and luck.

---

**Happy Mining! 🌙**
