# Night Miner Token Redeemer

**For miners who didn't consolidate before the airdrop snapshot.**

---

## The Problem

If you mined NIGHT tokens but didn't consolidate your mining wallet before the airdrop snapshot, you're stuck with hundreds of separate addresses. Each address holds a small portion of your tokens.

**The manual way:** Import each `.skey` file into Eternl, redeem NIGHT on the portal, repeat for every single address. With hundreds of addresses, this takes forever.

**This tool:** Automates the entire process. It batch-redeems tokens from all your mining addresses and consolidates everything to a single wallet.

---

## Developer Note

> **Please read this README thoroughly before using the tool.**
>
> I developed and tested this tool on Linux only, using a single unconsolidated mining address I had missed. Thorough testing would require both multiple mining addresses and real ADA on mainnet, so extensive multi-address testing has not been done with this tool. I am providing this tool as a courtesy to fellow miners who missed the consolidation window, since it's not something I personally need, I do not plan to invest further time or money into it's development.
>
> **I cannot guarantee it will work perfectly in all situations.**
>
> If you encounter issues or prefer not to use this tool, you can always import your mining wallet keys (`.skey` files) into [Eternl](https://eternl.io) and redeem your tokens manually through the official portal. This manual method will always work.

---

## What You Need

Before you start, make sure you have:

- [ ] Your **mining wallet files** (`addr-0.addr`, `addr-0.skey`, etc.)
- [ ] **Python** installed (see Step 1 below)
- [ ] A **Blockfrost API key** (free - the tool will guide you)
- [ ] Some **ADA** for transaction fees (I recommend you start with a minimal amount like 5-10 ADA to make sure the tool workflow works for you)

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

1. Click the green **"Code"** button at the top of the main night-miner main page
2. Click **"[Download ZIP](https://github.com/SL13PNIR/night-miner/archive/refs/heads/main.zip)"** 
3. Extract the ZIP file somewhere you'll remember (like your Desktop or Documents)
*Note: This will download all files, including the mining files and old consolidation tool. **We are only interested in the "night_redeemer" folder.***
---

## Step 3: Run Setup

Open the extracted folder. Inside the "night_redeemer" folder, you'll see:
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

## Alternative: Manual Installation

If the setup scripts don't work or you prefer to set things up yourself:

### 1. Create the folder structure

```bash
mkdir night-redeemer
mkdir night-redeemer/mining-wallet
mkdir night-redeemer/fee-wallet
mkdir night-redeemer/logs
```

### 2. Copy the script

Copy `night_redeemer.py` into the `night-redeemer` folder.

### 3. Create a virtual environment

```bash
cd night-redeemer

# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install pycardano requests
```

### 5. Run the tool

```bash
# With venv activated:
python night_redeemer.py
```

**Note:** You'll need to activate the virtual environment each time before running:
```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```


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
   - You'll need ~3.25 ADA per address to redeem

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

## After Redemption: What to Expect

When you redeem tokens, you may see **two UTXOs** appear for each mining address:

1. **Thawed tokens** → Sent directly to your mining address (spendable immediately)
2. **Locked tokens** → Held at a script address (unavailable until they thaw)

**Don't panic if you see tokens at an unfamiliar script address with "unavailable" balance!** This is normal:

### Understanding the Script Address

The script address (starts with `addr1z...` instead of `addr1q...`) shares the same stake key as your mining address, which is why it appears in your wallet if you view it in Eternl or on a blockchain explorer. However, it's controlled by a Plutus smart contract, not your private key.

**Example from a real redemption:**

| Destination | NIGHT | ADA | Description |
|-------------|-------|-----|-------------|
| Mining address (`addr1q...`) | 1.42 | 1.16 | Thaw #1 - spendable now |
| Script address (`addr1z...`) | 4.25 | 1.66 | Thaws #2-4 - locked until dates |
| Network fee | - | ~0.42 | Actual transaction fee |
| **Total from fee wallet** | | **~3.24** | |

### Why a Script Address?

The script address appears to be a time-lock contract. The likely purpose:

- **Trustless vesting**: Once redeemed, your future tokens are on-chain. Even if Midnight's portal goes offline, the tokens are locked in a smart contract that will release them when the thaw dates pass.
- **One-time interaction with Midnight**: The initial redemption is the only time Midnight's API is required. Future claims from the script may only require interacting with the Cardano blockchain.

### Speculation: Future Redemption Costs

> **Note:** The following is speculation based on observed behavior and general Cardano patterns. It cannot be verified without testing another thaw redemption.

The ADA sent to the script address (~1.66 ADA in the example) is locked with your future tokens. When those thaws unlock, this ADA may cover the fees for claiming them - meaning **future redemptions might require little to no additional ADA from your fee wallet**.

If this is correct, the recommendation to "wait for all tokens to thaw" may be less critical from a fee perspective than initially stated. However, until this is tested, the safest approach is still to wait if possible.

### Verifying Your Locked Tokens

You can check the thaw schedule for any address:

```
https://mainnet.prod.gd.midnighttge.io/thaws/YOUR_ADDRESS/schedule
```

Replace `YOUR_ADDRESS` with your mining address (starts with `addr1...`).

The NIGHT amounts shown should match what you see at the script address.

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

Here's how costs work:

### Redemption (~3.25 ADA per address)

On Cardano, tokens can't exist alone - they must be attached to ADA (called "min UTxO"). When you redeem NIGHT tokens:

- **~2.8 ADA** travels with your tokens
- **~0.45 ADA** is the network fee

The ADA that travels with tokens is split between:
- Your mining address (with thawed tokens)
- The script address (with locked future tokens)

So while you need ~3.2 ADA available per address, most of it stays with your NIGHT tokens.

### Consolidation (~0.5 ADA per address)

When consolidating, you're moving tokens that already have ADA attached:

- The ADA at each mining address helps pay for consolidation
- You only need ~0.5 ADA extra per address from your fee wallet
- After consolidating, all your NIGHT + attached ADA ends up at your destination

### Example: 100 Mining Addresses

| Step | Fee Wallet Needed | What Happens |
|------|-------------------|--------------|
| Redeem | ~325 ADA | ~280 ADA travels with tokens, ~45 ADA in fees |
| Consolidate | ~50 ADA | Mining address ADA offsets most of this |
| **Total fees** | | **~95 ADA** |

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

Open an issue on this repository if you run into problems or post on the [Midnight subreddit](https://www.reddit.com/r/Midnight).
