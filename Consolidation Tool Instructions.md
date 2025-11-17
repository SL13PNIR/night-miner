# NIGHT Miner - Wallet Consolidation Tool Instructions

A complete step-by-step guide for consolidating your NIGHT mining solutions from multiple addresses to a single destination address.

---

## Table of Contents

1. [What This Tool Does](#what-this-tool-does)
2. [Before You Start](#before-you-start)
3. [Step 1: Install Python](#step-1-install-python)
4. [Step 2: Download the Tool](#step-2-download-the-tool)
5. [Step 3: Install Dependencies](#step-3-install-dependencies)
6. [Step 4: Prepare Your Destination Address](#step-4-prepare-your-destination-address)
7. [Step 5: Run the Tool](#step-5-run-the-tool)
8. [Understanding the Output](#understanding-the-output)
9. [Troubleshooting](#troubleshooting)
10. [Frequently Asked Questions](#frequently-asked-questions)

---

## What This Tool Does

The consolidation tool allows you to:
- Combine mining solutions from multiple wallet addresses into one destination address
- Automatically handle all current and future solutions
- Keep a record of all consolidations for your reference
- Retry failed consolidations easily

**Important:** This tool uses the official donate_to API. All your addresses (source and destination) must be registered at https://sm.midnight.gd before consolidation.

You can check if your address is registered by replacing the address in the following link with your destination address:

https://sm.midnight.gd/api/statistics/addr1q8dsfs49kqg8w95c6zg2y8ytdz9ajgv53rnu9kxk7w2r5pv67n6yqakfjqs54rt4rsuh4q3359ru6znqmnulaahh67sspt4a9d

If the address is registered, you will see values for crypto_receipts and night_allocation (even if those values are 0).

---

## Before You Start

### Requirements Checklist

- [ ] You have a wallet folder containing your address files (`.addr` and `.skey` files)
- [ ] You have a destination Cardano address (starts with `addr1`)
- [ ] Your destination address is **unused** (0 transactions on the blockchain)
- [ ] Your destination address is **registered** at https://sm.midnight.gd
- [ ] You have control of all addresses

**⚠️ IMPORTANT:** Registration CANNOT be done through this tool. You must register at https://sm.midnight.gd first.

---

## Step 1: Install Python

Python is the programming language this tool runs on. Don't worry - it's free and easy to install!

### For Windows Users

1. **Download Python:**
   - Visit https://www.python.org/downloads/
   - Click the yellow "Download Python 3.x.x" button (get the latest version)

2. **Install Python:**
   - Run the downloaded installer
   - ⚠️ **VERY IMPORTANT:** Check the box that says "Add Python to PATH"
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

3. **Verify Installation:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter
   - Type `python --version` and press Enter
   - You should see something like "Python 3.11.5"

### For Mac Users

1. **Download Python:**
   - Visit https://www.python.org/downloads/
   - Click "Download Python 3.x.x" for macOS

2. **Install Python:**
   - Open the downloaded `.pkg` file
   - Follow the installation wizard
   - Enter your password when prompted
   - Click "Install"

3. **Verify Installation:**
   - Open Terminal (press `Cmd + Space`, type "Terminal", press Enter)
   - Type `python3 --version` and press Enter
   - You should see something like "Python 3.11.5"

### For Linux Users

Most Linux distributions come with Python pre-installed. To check:

1. **Verify Python:**
   ```bash
   python3 --version
   ```

2. **If Python is not installed:**

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-tk
   ```

   **Fedora:**
   ```bash
   sudo dnf install python3 python3-pip python3-tkinter
   ```

   **Arch Linux:**
   ```bash
   sudo pacman -S python python-pip tk
   ```

---

## Step 2: Download the Tool

### Option A: Download Directly (Easiest)

1. **Visit the GitHub page:**
   - Go to: https://github.com/SL13PNIR/night-miner/blob/main/consolidate-wallet.py

2. **Download the file:**
   - Click the "Raw" button (top right of the code)
   - Right-click anywhere on the page
   - Select "Save As..." or "Save Page As..."
   - Save it as `consolidate-wallet.py` in a location you'll remember (e.g., Downloads folder)

### Option B: Clone the Repository (Advanced)

If you have Git installed:

```bash
git clone https://github.com/SL13PNIR/night-miner.git
cd night-miner
```

---

## Step 3: Install Dependencies

The tool needs some additional Python packages to work. This is a one-time setup.

### For Windows Users

1. **Open Command Prompt:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter

2. **Navigate to the tool location:**
   ```cmd
   cd Downloads
   ```
   (Replace "Downloads" with wherever you saved the file)

3. **Install dependencies:**
   ```cmd
   pip install requests cbor2 pynacl
   ```

4. **Wait for installation to complete.** You should see "Successfully installed..." messages.

### For Mac Users

1. **Open Terminal:**
   - Press `Cmd + Space`
   - Type "Terminal" and press Enter

2. **Navigate to the tool location:**
   ```bash
   cd Downloads
   ```
   (Replace "Downloads" with wherever you saved the file)

3. **Install dependencies:**
   ```bash
   pip3 install requests cbor2 pynacl
   ```

### For Linux Users

1. **Open Terminal**

2. **Navigate to the tool location:**
   ```bash
   cd ~/Downloads
   ```
   (Adjust path as needed)

3. **Install dependencies:**
   ```bash
   pip3 install requests cbor2 pynacl
   ```

---

## Step 4: Prepare Your Destination Address

Before running the tool, you need a destination address ready.

### Requirements for Destination Address:

1. **Must be a Cardano Shelley address** (starts with `addr1`)
2. **Must be completely unused** (0 transactions on the blockchain)
3. **Must be registered for mining** at https://sm.midnight.gd

### How to Get a Fresh Address:

1. **From your Cardano wallet** (Daedalus, Yoroi, etc.):
   - Generate a new receiving address
   - Copy the address (it will start with `addr1`)
   - **DO NOT send any ADA or tokens to this address yet!**

2. **Register the address:**
   - Visit https://sm.midnight.gd
   - Register your new address for mining
   - Wait a few minutes for registration to complete

3. **Verify the address is unused:**
   - Visit https://cardanoscan.io
   - Paste your address in the search bar
   - Confirm it shows "0 transactions"

---

## Step 5: Run the Tool

Now you're ready to consolidate your addresses!

### For Windows Users

1. **Open Command Prompt:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter

2. **Navigate to tool location:**
   ```cmd
   cd Downloads
   ```

3. **Run the tool:**
   ```cmd
   python consolidate-wallet.py
   ```

### For Mac & Linux Users

1. **Open Terminal**

2. **Navigate to tool location:**
   ```bash
   cd Downloads
   ```

3. **Run the tool:**
   ```bash
   python3 consolidate-wallet.py
   ```

### Following the Prompts

The tool will guide you through the process step-by-step:

1. **Welcome Screen:**
   - Read the information carefully
   - Press Enter to continue

2. **Select Wallet Folder:**
   - The tool will look for `auto-mine-wallet` folder by default
   - If found, confirm to use it
   - Otherwise, a folder browser will open - select your wallet folder
   - The folder should contain your `.addr` and `.skey` files

3. **Enter Destination Address:**
   - Paste your destination address (the one you prepared in Step 4)
   - The tool will validate the format
   - A browser will open to CardanoScan - verify 0 transactions
   - Confirm the address is unused
   - The tool will check if the address is registered

4. **Review Consolidation Plan:**
   - Check the list of addresses that will be consolidated
   - Read the important notes
   - Type `CONSOLIDATE` (in all caps) to proceed
   - Or type `back` to change something

5. **Consolidation Process:**
   - The tool will process each address
   - You'll see progress for each one
   - Wait for all addresses to complete

6. **Review Summary:**
   - Check successful consolidations
   - Note any failures or skipped addresses
   - Records will be saved automatically

7. **Retry Failures (Optional):**
   - If any addresses failed, you can retry them
   - Or skip to consolidate another wallet

8. **Consolidate Another Wallet (Optional):**
   - You can consolidate multiple wallets in one session
   - Choose to use the same destination or pick a new one

---

## Understanding the Output

### During Consolidation

You'll see messages like:

```
[1/5] Processing addr1qxyz...
  Signing message...
  Consolidating...
  ✅ Successfully consolidated address (ID: CON_12345)
```

### Summary Screen

```
======================================================================
                     Consolidation Summary
======================================================================

Total addresses:     5
Successful:          4
Skipped (unreg):     1
Failed:              0

Successful consolidations:
  ✅ [0] addr1abc...
     Consolidation ID: CON_12345
  ✅ [1] addr1def...
     Consolidation ID: CON_12346

📁 Consolidation records saved:
   Text file: C:\Users\YourName\Downloads\consolidation_records_20251112_143022.txt
```

### Saved Records

The following file is created for each consolidation session:

1. **Text File (`.txt`)** - Human-readable record with:
   - Consolidation date and time
   - Destination address
   - List of all origin addresses
   - Consolidation IDs
   - Important notes

**Keep this files safe!** They contain important information about your consolidations.

---

## Troubleshooting

### Common Issues and Solutions

#### "Python is not recognized as a command"

**Problem:** Python is not in your system PATH.

**Solution for Windows:**
1. Uninstall Python
2. Reinstall Python
3. Make sure to check "Add Python to PATH" during installation

**Solution for Mac/Linux:**
- Use `python3` instead of `python` in all commands

---

#### "No module named 'requests'" (or 'cbor2', 'pynacl')

**Problem:** Dependencies are not installed.

**Solution:**
```bash
# Windows
pip install requests cbor2 pynacl

# Mac/Linux
pip3 install requests cbor2 pynacl
```

---

#### "Address is not registered for mining"

**Problem:** The address has not been registered at https://sm.midnight.gd

**Solution:**
1. Visit https://sm.midnight.gd
2. Register the address
3. Wait a few minutes
4. Try again using the "retry" option in the tool

---

#### "Address must be unused (0 transactions)"

**Problem:** The destination address has been used before.

**Solution:**
1. Generate a fresh address from your wallet
2. Do NOT send anything to it
3. Register it at https://sm.midnight.gd
4. Use the new address for consolidation

---

#### "Invalid signature" error

**Problem:** There may be an issue with the key files.

**Solution:**
1. Verify your `.skey` files are not corrupted
2. Make sure the wallet folder contains matching `.addr` and `.skey` files
3. If the problem persists, try consolidating addresses one at a time

---

#### Folder browser doesn't open

**Problem:** Tkinter (GUI library) is not working.

**Solution for Linux:**
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

**Workaround:** Manually place your wallet folder in the same directory as the tool and name it `auto-mine-wallet`.

---

#### "Failed to check registration after multiple retries"

**Problem:** Network connection or API server issues.

**Solution:**
1. Check your internet connection
2. Wait a few minutes and try again
3. The API server may be temporarily unavailable

---

## Frequently Asked Questions

### Q: Is this tool safe to use?

**A:** Yes! This tool:
- Is open source - you can review the code
- Uses the official donate_to API
- Does not send your private keys anywhere
- Only signs messages locally on your computer

### Q: Will I lose my solutions?

**A:** No. Consolidation transfers solution accumulation rights to your destination address. All past and future solutions from your source addresses will accumulate at the destination.

### Q: Can I undo a consolidation?

**A:** Yes! Run the tool again and consolidate from the origin address back to itself. This will undo the previous assignment.

### Q: Do I need to keep the source addresses?

**A:** The source addresses will continue to mine and accumulate solutions at the destination. However, you can decommission them if you want. Keep the consolidation records for reference.

### Q: How many addresses can I consolidate?

**A:** There's no technical limit. You can consolidate as many addresses as you want to a single destination. You can also consolidate multiple wallets in one session.

### Q: What if some addresses fail?

**A:** The tool will show you which addresses failed and why. You can retry failed addresses immediately, or run the tool again later. Successful consolidations are already saved.

### Q: Do I need to pay fees?

**A:** The consolidation API itself doesn't charge fees. When you eventually redeem your NIGHT tokens, there will likely be transaction fees involved.

### Q: Can I consolidate to an address that already has transactions?

**A:** No. The destination address must be completely unused (0 transactions) on the Cardano blockchain. This is a requirement to ensure clean consolidation.

### Q: Can I consolidate addresses from different wallets?

**A:** Yes! After consolidating one wallet, the tool will ask if you want to consolidate another. You can use the same destination address for multiple wallets.

### Q: What happens to my solutions after consolidation?

**A:** All current solutions from your source addresses are assigned to the destination after the mining period ends. This includes all past and future solutions mined by your source addresses.

### Q: How do I know if consolidation was successful?

**A:** The tool will show a checkmark (✅) and a consolidation ID for each successful address. A record file is also saved with all the details.

### Q: Do I need to run the tool multiple times?

**A:** No, you only need to run it once per wallet. However, you can run it multiple times to:
- Consolidate additional wallets
- Retry failed addresses
- Undo previous consolidations

*Don't forget that the miner my make additional addresses, so be sure to remember to consolidate those too!*

---

## Additional Help

### Need More Support?

- **GitHub Issues:** https://github.com/SL13PNIR/night-miner/issues
- **Reddit Post on the subject:** https://www.reddit.com/r/Midnight/comments/1ovc980/comment/noizlyr/

### Keeping Your Records Safe

After consolidation, make sure to:
1. Save the consolidation record file (`.txt`) to a safe location
2. Back them up to cloud storage or external drive
3. Keep them with your other wallet documentation

---

## Summary Checklist

Before you close this guide, make sure you've:

- [ ] Installed Python correctly
- [ ] Downloaded the consolidation tool
- [ ] Installed all dependencies (requests, cbor2, pynacl)
- [ ] Prepared a fresh, unused destination address
- [ ] Registered all addresses at https://sm.midnight.gd
- [ ] Successfully run the tool
- [ ] Saved your consolidation records

**Congratulations!** Your mining solutions are now consolidated. All future solutions from your source addresses will accumulate at your destination address automatically.

---

*Last Updated: November 2024*
*Tool Version: Latest from https://github.com/SL13PNIR/night-miner*





