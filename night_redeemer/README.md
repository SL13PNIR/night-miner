# Night Miner Token Redeemer

**For miners who didn't consolidate before the airdrop snapshot.**

---

## The Problem

If you mined NIGHT tokens but didn't consolidate your mining wallet before the airdrop snapshot, you're stuck with hundreds of separate addresses. Each address holds a small portion of your tokens.

**The manual way:** Import each `.skey` file into Eternl, redeem NIGHT on the portal, repeat for every single address. With hundreds of addresses, this takes forever.

**This tool:** Automates the entire process. It batch-redeems tokens from all your mining addresses and consolidates everything to a single wallet.

---

## What You Need

Before you start, make sure you have:

- [ ] Your **mining wallet files** (`addr-0.addr`, `addr-0.skey`, etc.)
- [ ] **Python** installed (see Step 1 below)
- [ ] A **Blockfrost API key** (free - the tool will guide you)
- [ ] Some **ADA** for transaction fees (~5 ADA to start)

---

## Step 1: Install Python (if you don't have it)

The tool requires Python. Check if you already have it:

**Windows:** Open Command Prompt and type `python --version`
**Mac/Linux:** Open Terminal and type `python3 --version`

If you see "Python 3.x.x", you're good - skip to Step 2.

If not, install Python:

### Windows
1. Go to **https://www.python.org/downloads/**
2. Click the big yellow "Download Python 3.x" button
3. Run the downloaded installer
4. **IMPORTANT:** Check the box that says **"Add Python to PATH"**
5. Click "Install Now"
6. Restart your computer

### Mac
1. Go to **https://www.python.org/downloads/**
2. Download the macOS installer
3. Run it and follow the prompts

### Linux
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip
```

---

## Step 2: Download This Tool

1. Click the green **"Code"** button at the top of this page
2. Click **"[Download ZIP](https://github.com/SL13PNIR/night-miner/archive/refs/heads/main.zip)"** 
3. Extract the ZIP file somewhere you'll remember (like your Desktop or Documents)

---

## Step 3: Run Setup

Open the extracted folder. You'll see:
- `setup-linux-mac.sh` (for Linux/Mac)
- `setup-windows.bat` (for Windows)
- `night_redeemer.py`
- `README.md`
- `SETUP_FILES.txt`

### Windows
Double-click **`setup-windows.bat`**

### Mac / Linux
Open Terminal in the folder and run:
```bash
chmod +x setup-linux-mac.sh
./setup-linux-mac.sh
```

Setup will create a `night-redeemer` folder with everything installed.

---

## Step 4: Add Your Mining Wallet

Open the `night-redeemer` folder that was just created.

Copy your mining wallet files into the `mining-wallet` subfolder:

```
night-redeemer/
└── mining-wallet/
    ├── addr-0.addr
    ├── addr-0.skey
    ├── addr-1.addr
    ├── addr-1.skey
    └── ... (all your mining address files)
```

These are the files you created when you set up Midnight mining. They're usually in a folder called `auto-mine-wallet` or similar.

---

## Step 5: Run the Tool

Open the `night-redeemer` folder.

### Windows
Double-click **`run.bat`**

### Mac / Linux
```bash
cd night-redeemer
./run.sh
```

---

## Using the Tool

When you run it, you'll see this menu:

```
=======================================================
        Night Miner Token Redeemer v1.0.0
=======================================================

  [1] Refresh Schedules    - Fetch latest thaw data from API
  [2] View Schedules       - See redeemable & upcoming thaws
  [3] Redeem Tokens        - Claim your thawed NIGHT tokens
  [4] Consolidate          - Send all NIGHT to one wallet
  [5] Settings             - Configure wallet, API key, etc.

  [q] Quit
```

### First Time Setup

1. The tool will ask for your **Blockfrost API key**
   - It will offer to open the website for you
   - Sign up (free) and create a project (select Cardano → Mainnet)
   - Copy your API key and paste it when asked

2. Go to **[5] Settings → Fee Wallet** to create your fee wallet

3. Send some ADA to your fee wallet address (shown in Settings)
   - Start with 5-10 ADA
   - You'll need ~3.5 ADA per address to redeem

### Menu Options Explained

| Option | What It Does |
|--------|--------------|
| **[1] Refresh Schedules** | Fetches the latest thaw data from the Midnight API for all your mining addresses. Shows which tokens are redeemable now vs still locked. |
| **[2] View Schedules** | Displays your tokens organized by status: "Redeemable Now" and "Upcoming Thaws" (grouped by unlock date). |
| **[3] Redeem Tokens** | Claims your thawed NIGHT tokens from all mining addresses that have redeemable tokens. |
| **[4] Consolidate** | Sends all your redeemed NIGHT tokens from mining addresses to a single destination wallet. Also offers to send remaining fee wallet ADA to your destination. |
| **[5] Settings** | Configure wallet directory, Blockfrost API key, and fee wallet. You can also drain your fee wallet here. |

### Recommended Workflow

**IMPORTANT: Wait for ALL tokens to thaw before redeeming!**

Redemption and consolidation cost fees. If you do them multiple times (e.g., redeem half now, half later), you pay fees twice. For lowest cost:

1. **[1] Refresh Schedules** - Check current status
2. **[2] View Schedules** - See what's redeemable vs upcoming
3. **Wait until all thawed** - Check back periodically (days/weeks)
4. **[3] Redeem Tokens** - Batch redeem ALL tokens at once
5. **[4] Consolidate** - Send ALL NIGHT to your wallet (once)
6. **Drain fee wallet** - Tool offers to send remaining ADA to your destination

When "Upcoming Thaws" in View Schedules is empty, all your tokens are ready!

---

## Folder Structure

After setup:

```
(extracted folder)/             <- Downloaded from GitHub
├── README.md
├── SETUP_FILES.txt
├── night_redeemer.py
├── setup-linux-mac.sh
├── setup-windows.bat
│
└── night-redeemer/             <- Created by setup (work here)
    ├── run.sh / run.bat        <- Run this to start
    ├── night_redeemer.py
    ├── mining-wallet/          <- Put your wallet keys here
    ├── fee-wallet/
    ├── logs/
    └── venv/
```

---

## Transaction Costs

**You're not losing 3.5 ADA per address!** Here's how costs actually work:

### Redemption (~3.5 ADA per address)

On Cardano, tokens can't travel alone - they must be attached to a small amount of ADA (called "min UTxO"). When you redeem NIGHT tokens:

- **~3.2 ADA** travels WITH your tokens (you keep this!)
- **~0.3 ADA** is the actual network fee (this is spent)

So while you need ~3.5 ADA available per address, most of it stays with your NIGHT tokens. After redemption, each mining address will hold NIGHT + ~3.2 ADA.

### Consolidation (~0.5 ADA per address)

When consolidating, you're moving tokens that already have ADA attached:

- The ~3.2 ADA from each mining address helps pay for consolidation
- You only need ~0.5 ADA extra per address from your fee wallet
- After consolidating, all your NIGHT + attached ADA ends up at your destination

### Example: 100 Mining Addresses

| Step | Fee Wallet Needed | What Happens |
|------|-------------------|--------------|
| Redeem | ~350 ADA | ~320 ADA travels with tokens, ~30 ADA in fees |
| Consolidate | ~50 ADA | Mining address ADA offsets most of this |
| **Total fees** | | **~80 ADA actual cost** (not 400 ADA!) |

The rest of your ADA ends up at your destination wallet along with your NIGHT.

---

## Troubleshooting

### "Python not found"

Make sure you installed Python and checked "Add to PATH" during installation. Restart your computer after installing.

### Linux: "Failed to create virtual environment" or pip errors

Install the required packages:
```bash
# Ubuntu/Debian
sudo apt install python3-venv python3-pip

# Fedora
sudo dnf install python3-pip python3-libs
```
Then delete the `night-redeemer` folder and run setup again.

### Windows: Nothing happens when I double-click the .bat file

Right-click the .bat file → "Run as administrator"

### "No wallet addresses found"

Make sure your `.addr` and `.skey` files are in the `night-redeemer/mining-wallet` folder.

### "Blockfrost connection failed"

- Check your API key is correct
- Make sure you chose "Cardano Mainnet" (not testnet) when creating the Blockfrost project

### Something went wrong

Check the `night-redeemer/logs/night_redeemer.log` file - it contains detailed information about what happened. You can share this file when asking for help.

---

## Security Notes

**Keep these files secret (never share):**
- `mining-wallet/*.skey` - Your mining wallet private keys
- `fee-wallet/fee-wallet.skey` - Your fee wallet private key

**Safe to share:**
- `*.addr` files - Just addresses, not keys
- Log files - Review first, but they don't contain private keys

**What this tool does NOT do:**
- Send your keys anywhere
- Store anything online
- Access anything except Cardano/Midnight APIs

All transaction signing happens locally on your computer.

---

## Questions?

Open an issue on this repository if you run into problems.
