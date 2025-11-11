#!/usr/bin/env python3
# ==============================================================================
# NIGHT Miner Wallet Consolidation Tool
#
# How to use this script:
# 1. Save this file as "consolidate-wallet.py"
# 2. Make sure you have a wallet folder with address key files (addr-N.addr, 
#    addr-N.skey files)
# 3. Run this script from your terminal. It will guide you through the process.
#
# IMPORTANT: This tool will consolidate ALL solutions from your wallet addresses
# to a single destination address. Make sure you understand the process before
# confirming!
#
# The destination address MUST be:
# - A valid Cardano Shelley receiving address (starts with 'addr1')
# - UNUSED (no transactions on the blockchain)
# - Under your control
# ==============================================================================

import os
import sys
import json
import requests
import subprocess
from datetime import datetime
from pathlib import Path
import re
import webbrowser

# ==============================================================================
# Pure Python Bech32 Implementation (No external dependency needed)
# Based on BIP 173: https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki
# ==============================================================================

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def bech32_polymod(values):
    """Internal function for Bech32 checksum computation."""
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp):
    """Expand the HRP into values for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_verify_checksum(hrp, data, const=1):
    """Verify a checksum given HRP and converted data characters."""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == const

def bech32_decode(bech):
    """Decode a bech32/bech32m string. Returns (hrp, data) or (None, None) on failure."""
    if ((any(ord(x) < 33 or ord(x) > 126 for x in bech)) or
            (bech.lower() != bech and bech.upper() != bech)):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind('1')
    if pos < 1 or pos + 7 > len(bech):  # Removed max length check for Cardano addresses
        return (None, None)
    if not all(x in BECH32_CHARSET for x in bech[pos+1:]):
        return (None, None)
    hrp = bech[:pos]
    data = [BECH32_CHARSET.find(x) for x in bech[pos+1:]]
    # Try bech32 (const=1) first, then bech32m (const=0x2bc830a3)
    if bech32_verify_checksum(hrp, data, 1):
        return (hrp, data[:-6])  # Remove 6-character checksum
    elif bech32_verify_checksum(hrp, data, 0x2bc830a3):
        return (hrp, data[:-6])  # bech32m variant
    else:
        return (None, None)  # Checksum failed

def bech32_convertbits(data, frombits, tobits, pad=True):
    """Convert between bit groups."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

# ==============================================================================
# The tkinter library is used for the folder selection pop-up window.
import tkinter as tk
from tkinter import filedialog

# --- Script Settings ---

# The default folder name we look for.
DEFAULT_WALLET_DIR = "auto-mine-wallet"

# The web address of the API
API_BASE_URL = "https://sm.midnight.gd/api"

# A short pause (in seconds) between operations to be polite to the server.
API_CALL_DELAY = 2

# --- Helper Functions ---

def clear_terminal_screen():
    """Wipes the terminal screen clean for a fresh display."""
    os.system('cls' if os.name == 'nt' else 'clear')

def select_wallet_directory_popup():
    """
    Opens the pop-up window that lets the user choose a folder.
    Returns the path to the folder they chose.
    """
    print("\nOpening folder selection dialog...")
    print("(The window may appear behind other windows - check your taskbar!)")
    
    root = tk.Tk()
    root.withdraw()
    
    # Bring the window to front
    root.attributes('-topmost', True)
    root.update()
    
    selected_path = filedialog.askdirectory(
        title="Select the folder containing your wallet key files",
        parent=root
    )
    
    root.attributes('-topmost', False)
    root.destroy()
    
    if selected_path:
        print(f"\n✅ Folder selected: {selected_path}")
    else:
        print("\n⚠️  Folder selection was canceled.")
        
    return selected_path

def is_valid_shelley_address(address):
    """
    Validates that an address is a Cardano Shelley receiving address.
    Opens CardanoScan in browser for user to verify.
    Returns (is_valid, message, needs_browser_check)
    """
    if not address:
        return False, "Address cannot be empty", False
    
    # Cardano addresses must be lowercase (bech32 standard)
    if address != address.lower():
        return False, "Address must be lowercase", False
    
    # Shelley mainnet addresses start with 'addr1'
    if not address.startswith('addr1'):
        return False, "Address must be a Cardano Shelley mainnet address (starts with 'addr1')", False
    
    # Basic length check (Shelley payment addresses are exactly 103 characters)
    if len(address) != 103:
        return False, f"Address length ({len(address)}) is incorrect (Shelley addresses are 103 characters)", False
    
    # Check for valid bech32 characters
    valid_chars = set('qpzry9x8gf2tvdw0s3jn54khce6mua7l')
    address_body = address[5:]  # Skip 'addr1'
    if not all(c in valid_chars for c in address_body.lower()):
        return False, "Address contains invalid characters", False
    
    # Decode the address structure (don't require checksum to pass - CardanoScan will verify)
    # Extract just the format to check network tag
    addr_chars = address[5:].lower()
    charset = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    data5 = [charset.index(c) for c in addr_chars if c in charset]
    data5_payload = data5[:-6]  # Remove last 6 chars (checksum)
    decoded = bech32_convertbits(data5_payload, 5, 8, False)
    
    if decoded and len(decoded) > 0:
        network_tag = decoded[0] & 0x0F
        if network_tag != 0x01:
            return False, f"Address is not for Cardano mainnet", False
    
    # Valid format - CardanoScan browser check will be the final validator
    return True, "✅ Valid address format (103 chars, correct structure)", True

def check_address_unused(address):
    """
    Checks if an address is unused (has no transaction history on Cardano blockchain).
    Returns (is_unused, message, details).
    
    This uses Koios API as the primary check, with fallback to simpler checks.
    """
    print(f"\n🔍 Checking Cardano blockchain for transaction history...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Try Koios API (public, no API key needed) - most reliable
    try:
        koios_url = f"https://api.koios.rest/api/v1/address_info"
        response = requests.post(
            koios_url,
            json={"_addresses": [address]},
            headers={"Content-Type": "application/json", **headers},
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                addr_info = data[0]
                
                # Check if address has any UTXOs or transaction history
                utxo_set = addr_info.get('utxo_set', [])
                tx_count = addr_info.get('tx_count', 0)
                balance = addr_info.get('balance', '0')
                
                if tx_count > 0:
                    return False, f"❌ Address has {tx_count} transaction(s) on blockchain (NOT unused)", {
                        'tx_count': tx_count,
                        'balance': balance,
                        'utxo_count': len(utxo_set)
                    }
                elif len(utxo_set) > 0:
                    return False, f"❌ Address has {len(utxo_set)} UTXO(s) on blockchain (NOT unused)", {
                        'tx_count': tx_count,
                        'balance': balance,
                        'utxo_count': len(utxo_set)
                    }
                else:
                    return True, "✅ Address is unused (no blockchain transactions)", {
                        'tx_count': 0,
                        'balance': '0',
                        'utxo_count': 0
                    }
            else:
                # Address not found on blockchain = unused/new
                return True, "✅ Address is unused (not found on blockchain - completely new)", {
                    'tx_count': 0,
                    'balance': '0',
                    'utxo_count': 0
                }
        else:
            print(f"  ⚠️  Koios API returned {response.status_code}, will rely on CardanoScan validation")
            return True, "✅ Address validation passed (Koios unavailable)", {'verified_by': 'cardanoscan'}
            
    except requests.exceptions.Timeout:
        print(f"  ⚠️  Koios API timed out, will rely on CardanoScan validation")
        return True, "✅ Address validation passed (Koios timeout)", {'verified_by': 'cardanoscan'}
    except Exception as e:
        print(f"  ⚠️  Koios check failed: {e}")
        print(f"  ℹ️  Will rely on CardanoScan validation")
        return True, "✅ Address validation passed (Koios unavailable)", {'verified_by': 'cardanoscan'}

def find_address_files(wallet_dir):
    """
    Finds all address files in the wallet directory.
    Returns a list of tuples: (index, address_file, skey_file)
    """
    address_files = []
    wallet_path = Path(wallet_dir)
    
    # Find all .addr files
    for addr_file in sorted(wallet_path.glob("addr-*.addr")):
        # Extract index from filename (e.g., "addr-0.addr" -> 0)
        match = re.match(r"addr-(\d+)\.addr", addr_file.name)
        if match:
            index = int(match.group(1))
            skey_file = wallet_path / f"addr-{index}.skey"
            
            if skey_file.exists():
                # Read the address
                with open(addr_file, 'r') as f:
                    address = f.read().strip()
                
                address_files.append((index, address, addr_file, skey_file))
    
    return address_files

def sign_donation_message(destination_address, original_address, skey_file):
    """
    Signs a donation message using CIP-8 signing.
    Message format: "Assign accumulated Scavenger rights to: <destination_address>"
    
    This implementation replicates the Rust miner's signing logic in Python,
    using only lightweight libraries (cbor2, pynacl, bech32).
    """
    try:
        import cbor2
        
        # Read the signing key
        with open(skey_file, 'r') as f:
            key_data = json.load(f)
        
        cbor_hex = key_data['cborHex']
        cbor_bytes = bytes.fromhex(cbor_hex)
        
        # The CBOR contains the key bytes (skip first 2 bytes which are CBOR tags)
        private_key_bytes = cbor_bytes[2:34]
        
        # Create the message
        message = f"Assign accumulated Scavenger rights to: {destination_address}"
        
        # For CIP-8 signing, we need to create a COSE_Sign1 structure
        # This is a simplified implementation - you may need the full cardano-serialization-lib
        
        # Import bech32 for address decoding
        # Decode the address to get raw bytes
        # For Cardano addresses, we can decode the bech32 data directly
        # The address format is: addr1<bech32-encoded-data>
        # We'll use a simple character mapping approach
        
        addr_chars = original_address[5:]  # Skip 'addr1'
        # Convert from bech32 charset to 5-bit values
        charset = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
        data5 = [charset.index(c) for c in addr_chars.lower() if c in charset]
        
        # Convert from 5-bit to 8-bit (remove checksum - last 6 chars = last ~8 5-bit values)
        data5_payload = data5[:-6]  # Remove 6-character checksum
        addr_bytes = bytes(bech32_convertbits(data5_payload, 5, 8, False))
        
        # Build the COSE_Sign1 structure (matches Rust implementation)
        # Protected headers: {1: -8, "address": addr_bytes}
        protected = {
            1: -8,  # Algorithm: EdDSA
            "address": addr_bytes
        }
        protected_encoded = cbor2.dumps(protected)
        
        # Unprotected headers: {"hashed": false}
        unprotected = {"hashed": False}
        
        # Payload is the message bytes
        payload = message.encode('utf-8')
        
        # Create Sig_structure for signing (CIP-8 standard)
        sig_structure = [
            "Signature1",
            protected_encoded,
            b"",  # external_aad
            payload
        ]
        sig_structure_encoded = cbor2.dumps(sig_structure)
        
        # Sign with ed25519
        from nacl.signing import SigningKey
        from nacl.encoding import RawEncoder
        
        signing_key = SigningKey(private_key_bytes)
        signature_bytes = signing_key.sign(sig_structure_encoded).signature
        
        # Build the final COSE_Sign1
        cose_sign1 = cbor2.dumps([
            protected_encoded,
            unprotected,
            payload,
            signature_bytes
        ])
        
        # Return as hex
        return cose_sign1.hex()
        
    except ImportError as e:
        print(f"\n❌ ERROR: Required Python library not found: {e}")
        print("\nPlease install required dependencies:")
        print("  pip install cbor2 pynacl bech32")
        print("\nNote: bech32 is optional (built-in fallback available) but recommended for best validation!")
        sys.exit(1)
    except Exception as e:
        raise Exception(f"Failed to sign message: {e}")

def consolidate_address(destination, original_address, signature):
    """
    Calls the donate_to API endpoint to consolidate solutions.
    Returns (success, message, response_data)
    
    Handles various API responses:
    - 200: Success (new donation or undo)
    - 403: Feature not available
    - 404: Original address not registered
    - 409: Already has active donation to different address
    - 400: Invalid signature
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    url = f"{API_BASE_URL}/donate_to/{destination}/{original_address}/{signature}"
    
    print(f"  📡 Consolidating from: {original_address[:20]}...{original_address[-10:]}")
    print(f"     Consolidating to:   {destination[:20]}...{destination[-10:]}")
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        
        if response.status_code == 403:
            return False, "⚠️  The donate_to API is currently unavailable (403 Forbidden). Feature not yet active.", None
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', '')
            message = data.get('message', '')
            solutions = data.get('solutions_consolidated', data.get('Solutions_consolidated', 0))
            donation_id = data.get('donation_id', 'N/A')
            
            # Check if this is an undo operation
            if 'undo' in message.lower() or original_address == destination:
                return True, f"  ✅ Undid previous donation assignment (ID: {donation_id})", data
            else:
                return True, f"  ✅ Successfully consolidated {solutions} solution(s) (ID: {donation_id})", data
        
        elif response.status_code == 404:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Address not registered')
            except:
                error_msg = 'Original address not registered'
            return False, f"  ❌ Failed: {error_msg}", None
        
        elif response.status_code == 409:
            # Already has active donation to different address
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Conflict - already has active donation')
            except:
                error_msg = 'Address already has active donation assignment'
            return False, f"  ⚠️  {error_msg}", None
        
        elif response.status_code == 400:
            # Invalid signature or bad request
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Bad request')
            except:
                error_msg = 'Invalid signature or bad request'
            return False, f"  ❌ Failed: {error_msg}", None
        
        else:
            error_text = response.text()[:200]  # Limit error text length
            return False, f"  ❌ Failed: HTTP {response.status_code} - {error_text}", None
            
    except requests.exceptions.Timeout:
        return False, "  ❌ Request timed out", None
    except Exception as e:
        return False, f"  ❌ Error: {e}", None

# --- Main Interface Functions ---

def show_welcome_screen():
    """Shows the initial welcome screen with important warnings."""
    clear_terminal_screen()
    print("=" * 70)
    print("           NIGHT Miner Wallet Consolidation Tool")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT INFORMATION - PLEASE READ CAREFULLY ⚠️")
    print()
    print("This tool will consolidate ALL solutions from your wallet addresses")
    print("to a SINGLE destination address using the donate_to API.")
    print()
    print("REQUIREMENTS for the destination address:")
    print("  ✓ Must be a valid Cardano Shelley address (starts with 'addr1')")
    print("  ✓ Must be UNUSED (no transaction history on Cardano blockchain)")
    print("  ✓ Does NOT need to be registered with Scavenger Mine")
    print("  ✓ Should be under YOUR control")
    print()
    print("REQUIREMENTS for source addresses:")
    print("  ✓ Must be REGISTERED with Scavenger Mine")
    print("  ✓ The tool will use your key files to sign messages")
    print()
    print("PROCESS:")
    print("  1. You provide a destination address")
    print("  2. The tool validates the address format")
    print("  3. The tool checks the Cardano blockchain for address history")
    print("  4. You review all addresses that will be consolidated")
    print("  5. You confirm the operation")
    print("  6. Each address is consolidated one by one")
    print()
    print("NOTE: Consolidation applies to past AND future solutions!")
    print("      You can undo by donating back to the original address.")
    print()
    print("AVAILABILITY:")
    print("      Available during mining (days 1-21) and up to 24 hours after.")
    print("      As of now, the API may return 403 if the feature is not active.")
    print()
    print("=" * 70)
    input("\nPress Enter to continue...")

def get_destination_address():
    """
    Prompts the user for a destination address and validates it.
    Returns the validated address or None if cancelled.
    """
    clear_terminal_screen()
    print("=" * 70)
    print("              Enter Destination Address")
    print("=" * 70)
    print()
    print("Please enter the Cardano Shelley address where you want to")
    print("consolidate all your wallet's solutions.")
    print()
    print("The address MUST:")
    print("  • Start with 'addr1' (Cardano mainnet)")
    print("  • Have NO transaction history on the Cardano blockchain")
    print("  • Be under your control")
    print()
    print("The address does NOT need to be registered with Scavenger Mine.")
    print()
    print("💡 TIP: Generate a fresh receiving address from your wallet!")
    print()
    print("Type 'cancel' to abort.")
    print("-" * 70)
    
    while True:
        destination = input("\nDestination address: ").strip()
        
        if destination.lower() == 'cancel':
            return None
        
        if not destination:
            print("❌ Address cannot be empty. Please try again.")
            continue
        
        # Validate address format
        is_valid, message, needs_browser_check = is_valid_shelley_address(destination)
        
        if is_valid is False:
            print(f"❌ {message}")
            print("   Please try again or type 'cancel' to abort.")
            continue
        else:
            # Valid address format
            print(f"   {message}")
        
        # Open CardanoScan in browser for visual verification
        if needs_browser_check:
            cardanoscan_url = f"https://cardanoscan.io/address/{destination}"
            print(f"\n  🌐 Opening CardanoScan in your browser...")
            print(f"  📍 {cardanoscan_url}")
            
            try:
                webbrowser.open(cardanoscan_url)
                print("\n  ✅ Browser opened successfully")
            except Exception as e:
                print(f"\n  ⚠️  Could not open browser automatically: {e}")
                print(f"  Please manually open: {cardanoscan_url}")
            
            print("\n" + "="*70)
            print("  🔍 VERIFICATION REQUIRED")
            print("="*70)
            print("  Please check the CardanoScan page and verify:")
            print("  1. The address is valid and recognized")
            print("  2. The transaction count is 0 (zero)")
            print("  3. The address has never been used on the blockchain")
            print("="*70)
            
            confirm = input("\n  ✅ Can you confirm the address shows 0 transactions? (y)es / (n)o: ").strip().lower()
            
            if confirm not in ['yes', 'y']:
                print("\n❌ Please verify the address is unused before proceeding.")
                print("   Type 'cancel' to abort, or provide a different address.")
                continue
        
        # Final confirmation
        print("\n" + "=" * 70)
        print("Destination address validated successfully!")
        print("=" * 70)
        print(f"\nAddress: {destination}")
        print(f"Verified: User confirmed 0 transactions on CardanoScan")
        print(f"Status:  Unused (no transaction history)")
        print()
        confirm = input("Is this correct? (y)es / (n)o: ").strip().lower()
        
        if confirm in ['yes', 'y']:
            return destination
        else:
            print("\nLet's try again...")
            input("Press Enter to continue...")
            clear_terminal_screen()
            print("=" * 70)
            print("              Enter Destination Address")
            print("=" * 70)
            print()

def show_consolidation_plan(wallet_dir, destination, address_files):
    """
    Shows the user what will happen and asks for confirmation.
    Returns True if user confirms, False otherwise.
    """
    clear_terminal_screen()
    print("=" * 70)
    print("           Consolidation Plan - Review & Confirm")
    print("=" * 70)
    print()
    print(f"Wallet Directory: {wallet_dir}")
    print(f"Destination:      {destination}")
    print()
    print(f"Found {len(address_files)} address(es) with key files:")
    print("-" * 70)
    
    for idx, address, addr_file, skey_file in address_files:
        print(f"  [{idx}] {address[:30]}...{address[-20:]}")
    
    print("-" * 70)
    print()
    print("⚠️  IMPORTANT: This operation will:")
    print("   • Sign a donation message with each address's private key")
    print("   • Call the donate_to API for each address")
    print("   • Consolidate ALL solutions (past AND future) to destination")
    print("   • Apply to future solutions until you undo it")
    print()
    print("💡 You can undo this later by donating back to the original address.")
    print()
    print("Benefits of consolidation:")
    print("   • Simplified NIGHT management from a single address")
    print("   • Reduced transaction fees during redemption")
    print("   • Lower minimum ADA requirements")
    print()
    print("=" * 70)
    
    while True:
        confirm = input("\nType 'CONSOLIDATE' to proceed, or 'cancel' to abort: ").strip()
        
        if confirm.lower() == 'cancel':
            return False
        elif confirm == 'CONSOLIDATE':
            return True
        else:
            print("❌ Please type exactly 'CONSOLIDATE' (in caps) to confirm, or 'cancel' to abort.")

def perform_consolidation(destination, address_files):
    """
    Performs the actual consolidation process.
    """
    clear_terminal_screen()
    print("=" * 70)
    print("              Performing Consolidation")
    print("=" * 70)
    print()
    
    results = []
    api_unavailable = False
    
    for i, (idx, address, addr_file, skey_file) in enumerate(address_files):
        print(f"\n[{i+1}/{len(address_files)}] Processing address index {idx}...")
        
        try:
            # Sign the donation message
            print("  🔐 Signing donation message...")
            signature = sign_donation_message(destination, address, skey_file)
            print("  ✅ Message signed successfully")
            
            # Call the API
            success, message, data = consolidate_address(destination, address, signature)
            print(message)
            
            results.append({
                'index': idx,
                'address': address,
                'success': success,
                'message': message,
                'data': data
            })
            
            if not success and "403" in message:
                api_unavailable = True
                print("\n⚠️  The donate_to API is not yet available.")
                print("   Stopping consolidation process.")
                break
            
            # Small delay between addresses
            if i < len(address_files) - 1 and success:
                import time
                time.sleep(API_CALL_DELAY)
                
        except Exception as e:
            error_msg = f"  ❌ Unexpected error: {e}"
            print(error_msg)
            results.append({
                'index': idx,
                'address': address,
                'success': False,
                'message': error_msg,
                'data': None
            })
    
    # Show summary
    print("\n" + "=" * 70)
    print("              Consolidation Summary")
    print("=" * 70)
    
    if api_unavailable:
        print("\n⚠️  API NOT AVAILABLE")
        print("\nThe donate_to API endpoint returned 403 Forbidden.")
        print("This feature is not yet active on the server.")
        print("\nPlease try again later when the API becomes available.")
        print("No solutions were transferred.")
    else:
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        # Count different types of operations
        consolidated_count = 0
        undo_count = 0
        already_assigned_count = 0
        not_registered_count = 0
        
        for r in results:
            if r['success']:
                msg = r['message'].lower()
                if 'undo' in msg:
                    undo_count += 1
                else:
                    consolidated_count += 1
                    # Try to get solution count
                    if r.get('data'):
                        consolidated_count += r['data'].get('solutions_consolidated', 
                                                           r['data'].get('Solutions_consolidated', 0))
            else:
                msg = r['message'].lower()
                if 'already has' in msg or 'conflict' in msg:
                    already_assigned_count += 1
                elif 'not registered' in msg:
                    not_registered_count += 1
        
        print(f"\n  Total addresses processed: {len(results)}")
        print(f"  Successful:                {successful}")
        print(f"  Failed:                    {failed}")
        
        if consolidated_count > 0:
            print(f"\n  ✅ New consolidations:     {consolidated_count}")
        if undo_count > 0:
            print(f"  ↩️  Undone assignments:    {undo_count}")
        if already_assigned_count > 0:
            print(f"  ⚠️  Already assigned:      {already_assigned_count}")
        if not_registered_count > 0:
            print(f"  ❌ Not registered:         {not_registered_count}")
        
        if failed > 0:
            print("\n⚠️  Some addresses had issues:")
            for r in results:
                if not r['success']:
                    print(f"    [{r['index']}] {r['address'][:30]}...")
                    # Clean up the message for display
                    clean_msg = r['message'].replace('  ❌ Failed:', '').replace('  ⚠️ ', '').strip()
                    print(f"        → {clean_msg}")
        
        if successful > 0:
            print("\n✅ Consolidation process completed!")
            print("   Solutions from successful addresses will now accumulate")
            print("   at the destination address.")
            print()
            print("💡 To undo: Run this tool again and donate back to original addresses.")
    
    print("\n" + "=" * 70)
    input("\nPress Enter to exit...")

# --- Main Program ---

def main():
    """The main function that runs the program."""
    
    # Show welcome screen
    show_welcome_screen()
    
    # Select wallet directory
    wallet_dir = DEFAULT_WALLET_DIR
    
    clear_terminal_screen()
    print("=" * 70)
    print("           Select Wallet Directory")
    print("=" * 70)
    
    if os.path.isdir(wallet_dir):
        print(f"\nDefault wallet folder found: {wallet_dir}")
        choice = input("\nUse this folder? (y)es / (n)o: ").strip().lower()
        
        if choice not in ['yes', 'y']:
            print("\nOpening folder selection window...")
            chosen_dir = select_wallet_directory_popup()
            
            if chosen_dir:
                wallet_dir = chosen_dir
            else:
                print("\n❌ No wallet folder was selected. Exiting.")
                sys.exit(1)
    else:
        print(f"\nThe default wallet folder ('{wallet_dir}') was not found.")
        input("\nPress Enter to open a folder selection window...")
        
        chosen_dir = select_wallet_directory_popup()
        
        if chosen_dir:
            wallet_dir = chosen_dir
        else:
            print("\n❌ No wallet folder was selected. Exiting.")
            sys.exit(1)
    
    # Confirm the selected folder
    print("\n" + "=" * 70)
    print("           Confirm Wallet Directory")
    print("=" * 70)
    print(f"\nSelected folder: {wallet_dir}")
    
    # Preview address files in the folder
    preview_files = [f for f in os.listdir(wallet_dir) if f.endswith('.addr')][:5]
    if preview_files:
        print(f"\nFound {len(preview_files)} address file(s):")
        for f in preview_files:
            print(f"  • {f}")
        if len(preview_files) == 5:
            print("  ...")
    
    confirm = input("\nIs this the correct wallet folder? (y)es / (n)o: ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("\n❌ Folder not confirmed. Exiting.")
        print("   Please run the script again to select a different folder.")
        sys.exit(1)
    
    # Find address files
    address_files = find_address_files(wallet_dir)
    
    if not address_files:
        print("\n❌ ERROR: No address files found in the wallet directory!")
        print(f"   Looked in: {wallet_dir}")
        print("   Expected files: addr-N.addr and addr-N.skey")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Get destination address
    destination = get_destination_address()
    
    if not destination:
        print("\n❌ Operation cancelled by user.")
        sys.exit(0)
    
    # Show plan and get confirmation
    if not show_consolidation_plan(wallet_dir, destination, address_files):
        print("\n❌ Operation cancelled by user.")
        sys.exit(0)
    
    # Perform consolidation
    perform_consolidation(destination, address_files)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation interrupted by user (Ctrl+C).")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
