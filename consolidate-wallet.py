#!/usr/bin/env python3
"""
NIGHT Miner Wallet Consolidation Tool

A tool for consolidating mining solutions from multiple wallet addresses generated with NIGHT miner
to a single destination address using the donate_to API.

Requirements:
- Python 3.7+
- All addresses must be registered at https://sm.midnight.gd
- Destination address must be unused on Cardano blockchain
"""

import os
import json
import time
import requests
import webbrowser
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
import re
import tkinter as tk
from tkinter import filedialog

# Configuration
CONFIG = {
    "statistics_api_base": "https://sm.midnight.gd/api",
    "donation_api_base": "https://scavenger.prod.gd.midnighttge.io",
    "api_call_delay": 2,
    "default_wallet_dir": "auto-mine-wallet",
    "request_timeout": 30,
    "max_retries": 3
}


# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class Address:
    """Represents a wallet address with associated files."""
    index: int
    address: str
    addr_file: Path
    skey_file: Path
    is_registered: bool = False
    has_solutions: int = 0


@dataclass
class ValidationResult:
    """Result of address validation."""
    is_valid: bool
    message: str
    needs_browser_check: bool = False
    details: Dict[str, Any] = None


@dataclass
class ConsolidationResult:
    """Result of a consolidation operation."""
    index: int
    address: str
    success: bool
    message: str
    donation_id: Optional[str] = None
    skipped_reason: Optional[str] = None


class NavigationAction(Enum):
    """Navigation actions for the UI."""
    CONTINUE = "continue"
    BACK = "back"
    CANCEL = "cancel"
    RETRY = "retry"


class OperationMode(Enum):
    """Operation modes for consolidation."""
    CONSOLIDATE = "consolidate"
    REMOVE_CONSOLIDATIONS = "remove"


# ==============================================================================
# Bech32 Utilities (Pure Python Implementation)
# ==============================================================================

class Bech32:
    """Bech32 encoding/decoding utilities for Cardano addresses."""

    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    @staticmethod
    def polymod(values):
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for value in values:
            b = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ value
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk

    @staticmethod
    def hrp_expand(hrp):
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    @staticmethod
    def verify_checksum(hrp, data, const=1):
        return Bech32.polymod(Bech32.hrp_expand(hrp) + data) == const

    @staticmethod
    def decode(bech):
        if ((any(ord(x) < 33 or ord(x) > 126 for x in bech)) or
                (bech.lower() != bech and bech.upper() != bech)):
            return None, None

        bech = bech.lower()
        pos = bech.rfind('1')
        if pos < 1 or pos + 7 > len(bech):
            return None, None

        if not all(x in Bech32.CHARSET for x in bech[pos+1:]):
            return None, None

        hrp = bech[:pos]
        data = [Bech32.CHARSET.find(x) for x in bech[pos+1:]]

        if Bech32.verify_checksum(hrp, data, 1):
            return hrp, data[:-6]
        elif Bech32.verify_checksum(hrp, data, 0x2bc830a3):
            return hrp, data[:-6]
        else:
            return None, None

    @staticmethod
    def convertbits(data, frombits, tobits, pad=True):
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
# API Client
# ==============================================================================

class APIClient:
    """Handles all API interactions with the NIGHT mining service."""

    def __init__(self):
        self.statistics_base = CONFIG["statistics_api_base"]
        self.donation_base = CONFIG["donation_api_base"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def check_registration(self, address: str) -> Tuple[bool, str, Dict]:
        """Check if an address is registered for mining."""
        url = f"{self.statistics_base}/statistics/{address}"

        for attempt in range(CONFIG["max_retries"]):
            try:
                response = self.session.get(url, timeout=CONFIG["request_timeout"])

                if response.status_code == 200:
                    data = response.json()
                    if data.get('local'):
                        receipts = data['local'].get('crypto_receipts', 0)
                        earnings = data['local'].get('night_allocation', 0)
                        return True, f"Registered (Receipts: {receipts}, Earnings: {earnings} STAR)", data
                    return False, "Address not found in mining registry", {}

                elif response.status_code in [400, 404]:
                    return False, "Address is not registered for mining", {}

                elif response.status_code == 429:
                    wait_time = min(20 * (2 ** attempt), 60)
                    if attempt < CONFIG["max_retries"] - 1:
                        time.sleep(wait_time)
                        continue
                    return False, "Rate limited by server", {}

                else:
                    return False, f"Server returned HTTP {response.status_code}", {}

            except requests.exceptions.RequestException as e:
                if attempt < CONFIG["max_retries"] - 1:
                    time.sleep(20 * (attempt + 1))
                    continue
                return False, f"Network error: {str(e)}", {}

        return False, "Failed to check registration", {}

    def consolidate_solutions(self, destination: str, source: str, signature: str) -> ConsolidationResult:
        """Call the donate_to API to consolidate solutions."""
        url = f"{self.donation_base}/donate_to/{destination}/{source}/{signature}"

        try:
            response = self.session.post(url, timeout=CONFIG["request_timeout"])

            if response.status_code == 200:
                data = response.json()
                donation_id = data.get('donation_id', 'N/A')
                message = data.get('message', '')

                if 'undo' in message.lower() or source == destination:
                    return ConsolidationResult(
                        index=0, address=source, success=True,
                        message="Undid previous donation assignment",
                        donation_id=donation_id
                    )
                return ConsolidationResult(
                    index=0, address=source, success=True,
                    message="Successfully consolidated address",
                    donation_id=donation_id
                )

            elif response.status_code == 403:
                return ConsolidationResult(
                    index=0, address=source, success=False,
                    message="API unavailable (403)",
                    skipped_reason="api_unavailable"
                )

            elif response.status_code == 404:
                return ConsolidationResult(
                    index=0, address=source, success=False,
                    message="Address not registered",
                    skipped_reason="not_registered"
                )

            elif response.status_code == 409:
                # Try to extract donation ID from 409 response
                donation_id = None
                try:
                    error_data = response.json()
                    donation_id = error_data.get('donation_id', None)
                    # Also check common alternative field names
                    if not donation_id:
                        donation_id = error_data.get('id', None)
                    if not donation_id:
                        donation_id = error_data.get('consolidation_id', None)
                except Exception:
                    pass

                return ConsolidationResult(
                    index=0, address=source, success=True,
                    message="Already consolidated (previous assignment active)",
                    donation_id=donation_id
                )

            elif response.status_code == 400:
                return ConsolidationResult(
                    index=0, address=source, success=False,
                    message="Invalid signature",
                    skipped_reason="signature_error"
                )

            else:
                return ConsolidationResult(
                    index=0, address=source, success=False,
                    message=f"HTTP {response.status_code}",
                    skipped_reason="server_error"
                )

        except Exception as e:
            return ConsolidationResult(
                index=0, address=source, success=False,
                message=str(e),
                skipped_reason="network_error"
            )


# ==============================================================================
# Address Validator
# ==============================================================================

class AddressValidator:
    """Validates Cardano addresses."""

    @staticmethod
    def validate_format(address: str) -> ValidationResult:
        """Validate address format and structure."""
        if not address:
            return ValidationResult(False, "Address cannot be empty")

        if address != address.lower():
            return ValidationResult(False, "Address must be lowercase")

        if not address.startswith('addr1'):
            return ValidationResult(False, "Must be a Cardano Shelley mainnet address")

        if len(address) != 103:
            return ValidationResult(
                False,
                f"Invalid length ({len(address)}) - should be 103 characters"
            )

        valid_chars = set('qpzry9x8gf2tvdw0s3jn54khce6mua7l')
        if not all(c in valid_chars for c in address[5:]):
            return ValidationResult(False, "Contains invalid characters")

        # Verify network tag
        try:
            addr_chars = address[5:]
            data5 = [Bech32.CHARSET.index(c) for c in addr_chars if c in Bech32.CHARSET]
            data5_payload = data5[:-6]
            decoded = Bech32.convertbits(data5_payload, 5, 8, False)

            if decoded and len(decoded) > 0:
                network_tag = decoded[0] & 0x0F
                if network_tag != 0x01:
                    return ValidationResult(False, "Not a mainnet address")
        except Exception:
            return ValidationResult(False, "Invalid address structure")

        return ValidationResult(
            True,
            "Valid address format",
            needs_browser_check=True
        )

    @staticmethod
    def open_cardanoscan(address: str) -> bool:
        """Open CardanoScan in browser for address verification."""
        url = f"https://cardanoscan.io/address/{address}"
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False


# ==============================================================================
# Wallet Manager
# ==============================================================================

class WalletManager:
    """Manages wallet files and signing operations."""

    def __init__(self, wallet_dir: str):
        self.wallet_dir = Path(wallet_dir)

    def find_addresses(self) -> List[Address]:
        """Find all address files in the wallet directory."""
        addresses = []

        for addr_file in sorted(self.wallet_dir.glob("addr-*.addr")):
            match = re.match(r"addr-(\d+)\.addr", addr_file.name)
            if match:
                index = int(match.group(1))
                skey_file = self.wallet_dir / f"addr-{index}.skey"

                if skey_file.exists():
                    with open(addr_file, 'r') as f:
                        address_str = f.read().strip()

                    addresses.append(Address(
                        index=index,
                        address=address_str,
                        addr_file=addr_file,
                        skey_file=skey_file
                    ))

        return addresses

    def sign_message(self, destination: str, source_address: Address) -> str:
        """Sign a donation message using CIP-8."""
        try:
            import cbor2
            from nacl.signing import SigningKey

            # Read signing key
            with open(source_address.skey_file, 'r') as f:
                key_data = json.load(f)

            cbor_hex = key_data['cborHex']
            cbor_bytes = bytes.fromhex(cbor_hex)
            private_key_bytes = cbor_bytes[2:34]

            # Create message
            message = f"Assign accumulated Scavenger rights to: {destination}"

            # Decode address
            addr_chars = source_address.address[5:]
            data5 = [Bech32.CHARSET.index(c) for c in addr_chars.lower() if c in Bech32.CHARSET]
            data5_payload = data5[:-6]
            addr_bytes = bytes(Bech32.convertbits(data5_payload, 5, 8, False))

            # Build COSE_Sign1 structure
            protected = {1: -8, "address": addr_bytes}
            protected_encoded = cbor2.dumps(protected)
            unprotected = {"hashed": False}
            payload = message.encode('utf-8')

            sig_structure = [
                "Signature1",
                protected_encoded,
                b"",
                payload
            ]
            sig_structure_encoded = cbor2.dumps(sig_structure)

            # Sign with ed25519
            signing_key = SigningKey(private_key_bytes)
            signature_bytes = signing_key.sign(sig_structure_encoded).signature

            # Build final COSE_Sign1
            cose_sign1 = cbor2.dumps([
                protected_encoded,
                unprotected,
                payload,
                signature_bytes
            ])

            return cose_sign1.hex()

        except ImportError:
            raise RuntimeError(
                "Required dependencies not found. Install with:\n"
                "pip install cbor2 pynacl"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to sign message: {e}")


# ==============================================================================
# UI Manager
# ==============================================================================

class UIManager:
    """Manages user interface and navigation."""

    @staticmethod
    def clear_screen():
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def display_header(title: str):
        """Display a formatted header."""
        UIManager.clear_screen()
        print("=" * 70)
        print(f"  {title.center(66)}")
        print("=" * 70)
        print()

    @staticmethod
    def display_separator():
        """Display a separator line."""
        print("-" * 70)

    @staticmethod
    def prompt_action(prompt: str, options: List[str]) -> str:
        """Prompt user for action with validation."""
        valid_options = [opt.lower() for opt in options]
        while True:
            response = input(f"\n{prompt}: ").strip().lower()
            if response in valid_options:
                return response
            print(f"Invalid option. Choose from: {', '.join(options)}")

    @staticmethod
    def prompt_confirmation(message: str) -> bool:
        """Prompt for yes/no confirmation."""
        response = UIManager.prompt_action(f"{message} (y/n)", ["y", "yes", "n", "no"])
        return response in ["y", "yes"]

    @staticmethod
    def select_folder() -> Optional[str]:
        """Open folder selection dialog."""
        print("\nOpening folder selection dialog...")
        print("(The window may appear behind other windows)")

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.update()

        selected_path = filedialog.askdirectory(
            title="Select wallet folder containing key files"
        )

        root.attributes('-topmost', False)
        root.destroy()

        return selected_path if selected_path else None

    @staticmethod
    def display_progress(current: int, total: int, message: str):
        """Display progress indicator."""
        print(f"\n[{current}/{total}] {message}")

    @staticmethod
    def display_summary(results: List[ConsolidationResult], record_file: Optional[str] = None):
        """Display consolidation summary."""
        print("\n" + "=" * 70)
        print("  Consolidation Summary".center(70))
        print("=" * 70)

        successful = [r for r in results if r.success]
        skipped = [r for r in results if r.skipped_reason == "not_registered"]
        failed = [r for r in results if not r.success and r.skipped_reason != "not_registered"]

        print(f"\nTotal addresses:     {len(results)}")
        print(f"Successful:          {len(successful)}")
        print(f"Skipped (unreg):     {len(skipped)}")
        print(f"Failed:              {len(failed)}")

        if successful:
            print("\nSuccessful consolidations:")
            for r in successful:
                if r.donation_id:
                    print(f"  ✅ [{r.index}] {r.address[:40]}...")
                    print(f"     Consolidation ID: {r.donation_id}")
                else:
                    print(f"  ✅ [{r.index}] {r.address[:40]}... (already consolidated)")

        if skipped:
            print("\nUnregistered addresses (skipped):")
            for r in skipped:
                print(f"  ⚠️ [{r.index}] {r.address[:40]}...")

        if failed:
            print("\nFailed addresses:")
            for r in failed:
                print(f"  ❌ [{r.index}] {r.address[:40]}...")
                print(f"     Reason: {r.message}")

        if record_file:
            # Show both files
            json_file = record_file.replace('.txt', '.json')
            print(f"\n📁 Consolidation records saved:")
            print(f"   Text file: {record_file}")

        print("\n" + "=" * 70)


# ==============================================================================
# Navigation Controller
# ==============================================================================

class NavigationController:
    """Manages application navigation flow."""

    def __init__(self):
        self.stack = []
        self.current_state = "welcome"

    def push_state(self, state: str):
        """Push a new state onto the navigation stack."""
        self.stack.append(self.current_state)
        self.current_state = state

    def pop_state(self) -> Optional[str]:
        """Go back to previous state."""
        if self.stack:
            self.current_state = self.stack.pop()
            return self.current_state
        return None

    def reset(self):
        """Reset navigation to initial state."""
        self.stack = []
        self.current_state = "welcome"


# ==============================================================================
# Consolidation Controller
# ==============================================================================

class ConsolidationController:
    """Main application controller."""

    def __init__(self):
        self.api_client = APIClient()
        self.ui = UIManager()
        self.nav = NavigationController()
        self.wallet_manager = None
        self.wallet_dir = None
        self.addresses = []
        self.destination = None
        self.consolidation_records = []
        self.operation_mode = None

    def run(self):
        """Main application entry point."""
        try:
            # Show welcome only once
            if not self.show_welcome():
                return

            # Main consolidation loop
            while True:
                self.nav.reset()
                self.nav.push_state("select_wallet")

                # Process one wallet
                if not self.process_wallet_consolidation():
                    break

                # Ask if user wants to consolidate another wallet
                if not self.ask_continue_with_another_wallet():
                    break

        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user (Ctrl+C)")
        except Exception as e:
            print(f"\n\nUnexpected error: {e}")
            input("Press Enter to exit...")

    def process_wallet_consolidation(self) -> bool:
        """Process a single wallet consolidation workflow."""
        while True:
            if self.nav.current_state == "select_wallet":
                if not self.select_wallet():
                    if not self.nav.pop_state():
                        return False

            elif self.nav.current_state == "select_operation_mode":
                if not self.select_operation_mode():
                    if not self.nav.pop_state():
                        return False

            elif self.nav.current_state == "select_destination":
                if not self.select_destination():
                    if not self.nav.pop_state():
                        return False

            elif self.nav.current_state == "confirm_plan":
                if not self.confirm_plan():
                    if not self.nav.pop_state():
                        return False

            elif self.nav.current_state == "execute":
                self.execute_consolidation_with_retry()
                return True

            else:
                return False

    def ask_continue_with_another_wallet(self) -> bool:
        """Ask if user wants to consolidate another wallet."""
        print("\n" + "=" * 70)
        print("  Continue with Another Wallet?".center(70))
        print("=" * 70)

        if self.ui.prompt_confirmation("\nWould you like to process another wallet"):
            # Check current mode before resetting
            was_consolidate_mode = self.operation_mode == OperationMode.CONSOLIDATE

            # Reset addresses and operation mode
            self.addresses = []
            self.wallet_manager = None
            self.wallet_dir = None
            self.operation_mode = None

            # Ask about destination address only if previous operation was consolidate mode
            if self.destination and was_consolidate_mode:
                print(f"\nCurrent destination: {self.destination[:40]}...")
                if self.ui.prompt_confirmation("Use the same destination address"):
                    # Keep the current destination
                    self.nav.reset()
                    self.nav.push_state("select_wallet")
                else:
                    # Clear destination for new selection
                    self.destination = None
                    self.nav.reset()
                    self.nav.push_state("select_wallet")
            else:
                # Clear destination for new selection
                self.destination = None
                self.nav.reset()
                self.nav.push_state("select_wallet")
            return True
        return False

    def show_welcome(self) -> bool:
        """Show welcome screen."""
        self.ui.display_header("NIGHT Miner Wallet Consolidation Tool")

        print("This tool manages consolidation of mining rewards from multiple")
        print("addresses. You can consolidate to a destination or remove existing")
        print("consolidations.\n")

        print("REQUIREMENTS:")
        print("• All addresses must be registered at https://sm.midnight.gd")
        print("• For consolidation: destination must be unused on Cardano blockchain")
        print("• You must have control of all addresses\n")

        print("MODES:")
        print("• CONSOLIDATE - Assign earned rewards to a destination address")
        print("• REMOVE CONSOLIDATIONS - Undo existing consolidations\n")

        print("IMPORTANT:")
        print("• You can continue mining on existing generated addresses")
        print("• Consolidation assigns rewards earned in the past, present and future to the destination address")
        print("• Rewards will not be assigned to the destination address until after the mining period is over")
        print("• Rewards must be redeemed manually on the website during the redemption period\n")

        print("PROCESS:")
        print("1. Select wallet folder")
        print("2. Choose operation mode")
        print("3. Enter destination (if consolidating)")
        print("4. Review and execute\n")

        if self.ui.prompt_confirmation("Continue"):
            self.nav.push_state("select_wallet")
            return True
        return False

    def select_wallet(self) -> bool:
        """Select and validate wallet directory."""
        self.ui.display_header("Select Wallet Directory")

        # Check for default directory
        default_dir = CONFIG["default_wallet_dir"]
        if os.path.isdir(default_dir):
            print(f"Default wallet found: {default_dir}")
            if self.ui.prompt_confirmation("Use this folder"):
                self.wallet_dir = default_dir
            else:
                self.wallet_dir = self.ui.select_folder()
        else:
            print("Default wallet not found.")
            input("Press Enter to browse for wallet...")
            self.wallet_dir = self.ui.select_folder()

        if not self.wallet_dir:
            print("\nNo folder selected.")
            return False

        # Load addresses
        self.wallet_manager = WalletManager(self.wallet_dir)
        self.addresses = self.wallet_manager.find_addresses()

        if not self.addresses:
            print(f"\nNo address files found in: {self.wallet_dir}")
            if self.ui.prompt_confirmation("Try different folder"):
                return self.select_wallet()
            return False

        print(f"\nFound {len(self.addresses)} address(es)")

        # Always ask for operation mode after wallet selection
        self.nav.push_state("select_operation_mode")
        return True

    def select_operation_mode(self) -> bool:
        """Select operation mode: consolidate or remove consolidations."""
        self.ui.display_header("Select Operation Mode")

        print("Choose an operation:")
        print("\n1. CONSOLIDATE - Assign earned rewards to a destination address")
        print("   All current and future rewards will be assigned to the destination.")
        print("\n2. REMOVE CONSOLIDATIONS - Undo existing consolidations")
        print("   Returns reward assignments to their original addresses (origin = destination).")
        print()

        while True:
            choice = input("Enter choice (1/2 or 'back'): ").strip()

            if choice.lower() == 'back':
                return False

            if choice == '1':
                self.operation_mode = OperationMode.CONSOLIDATE
                # If destination is already set from previous operation, skip to confirmation
                if self.destination:
                    self.nav.push_state("confirm_plan")
                else:
                    self.nav.push_state("select_destination")
                return True
            elif choice == '2':
                self.operation_mode = OperationMode.REMOVE_CONSOLIDATIONS
                # For remove mode, destination is automatically handled (same as origin)
                self.destination = None  # Clear any previous destination
                self.nav.push_state("confirm_plan")
                return True
            else:
                print("Invalid choice. Please enter 1 or 2.")

    def select_destination(self) -> bool:
        """Select and validate destination address."""
        self.ui.display_header("Enter Destination Address")

        print("Enter the Cardano address where rewards will be assigned.")
        print("The address must:")
        print("• Start with 'addr1'")
        print("• Have no transaction history")
        print("• Be registered for mining\n")

        while True:
            destination = input("Destination address (or 'back'): ").strip()

            if destination.lower() == 'back':
                return False

            # Validate format
            validation = AddressValidator.validate_format(destination)
            if not validation.is_valid:
                print(f"\n❌ {validation.message}")
                continue

            print(f"\n✅ {validation.message}")

            # Check blockchain history
            if validation.needs_browser_check:
                print("\n🌐 Opening CardanoScan for verification...")
                AddressValidator.open_cardanoscan(destination)
                print("    Please verify the address shows 0 transactions.")

                if not self.ui.prompt_confirmation(
                    "\nDoes CardanoScan show 0 transactions"
                ):
                    print("\n⚠️  Address must be unused (0 transactions) to consolidate.")
                    continue

                print("✅ Blockchain verification confirmed by user")

            # Check registration
            print("\n🔍 Checking mining registration status...")
            print("   (This may take a few seconds...)")
            is_registered, message, _ = self.api_client.check_registration(destination)

            if not is_registered:
                print(f"\n❌ {message}")
                print("\nRegister at: https://sm.midnight.gd")

                action = self.ui.prompt_action(
                    "Action", ["retry", "new", "back"]
                )
                if action == "retry":
                    continue
                elif action == "back":
                    return False
                else:
                    continue

            print(f"\n✅ {message}")
            self.destination = destination
            self.nav.push_state("confirm_plan")
            return True

    def confirm_plan(self) -> bool:
        """Display and confirm consolidation plan."""
        if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
            self.ui.display_header("Review Remove Consolidations Plan")

            print(f"Wallet: {self.wallet_dir}\n")
            print(f"Operation: REMOVE CONSOLIDATIONS")
            print(f"Addresses to process: {len(self.addresses)}")
            self.ui.display_separator()

            for addr in self.addresses[:5]:
                print(f"  [{addr.index}] {addr.address[:40]}...")
            if len(self.addresses) > 5:
                print(f"  ... and {len(self.addresses) - 5} more")

            self.ui.display_separator()
            print("\nThis will UNDO existing consolidations by setting origin = destination.")
            print("Rewards will be assigned back to their original addresses.")
            print("\n📁 A record of all successful operations will be saved.")
            print("\nYou can retry any failed operations after the initial attempt.")

            confirm = input("\nType 'REMOVE' to proceed or 'back': ").strip()

            if confirm == 'REMOVE':
                self.nav.push_state("execute")
                return True
            elif confirm.lower() == 'back':
                return False

            print("Please type exactly 'REMOVE' to confirm.")
            return self.confirm_plan()

        else:  # CONSOLIDATE mode
            self.ui.display_header("Review Consolidation Plan")

            print(f"Wallet:      {self.wallet_dir}")
            print(f"Destination: {self.destination}\n")

            print(f"Addresses to consolidate: {len(self.addresses)}")
            self.ui.display_separator()

            for addr in self.addresses[:5]:
                print(f"  [{addr.index}] {addr.address[:40]}...")
            if len(self.addresses) > 5:
                print(f"  ... and {len(self.addresses) - 5} more")

            self.ui.display_separator()
            print("\nThis will assign all current and future rewards to the destination.")
            print("Rewards are earned after mining period ends and must be redeemed separately.")
            print("\n📁 A record of all successful consolidations will be saved with:")
            print("   • Origin addresses")
            print("   • Destination address")
            print("   • Consolidation IDs")
            print("\nYou can retry any failed consolidations after the initial attempt.")

            confirm = input("\nType 'CONSOLIDATE' to proceed or 'back': ").strip()

            if confirm == 'CONSOLIDATE':
                self.nav.push_state("execute")
                return True
            elif confirm.lower() == 'back':
                return False

            print("Please type exactly 'CONSOLIDATE' to confirm.")
            return self.confirm_plan()

    def save_consolidation_records(self, results: List[ConsolidationResult]) -> Optional[str]:
        """Save consolidation records."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
            txt_file = f"remove_consolidation_records_{timestamp}.txt"
        else:
            txt_file = f"consolidation_records_{timestamp}.txt"

        records = []
        for r in results:
            if r.success and r.donation_id:
                if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
                    records.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "address": r.address,
                        "consolidation_id": r.donation_id
                    })
                else:
                    records.append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "origin_address": r.address,
                        "destination_address": self.destination,
                        "consolidation_id": r.donation_id
                    })

        if records:
            # Save TXT file (for end users)
            txt_path = os.path.abspath(txt_file)
            with open(txt_path, 'w') as f:
                f.write("=" * 70 + "\n")

                if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
                    f.write("NIGHT Miner - Remove Consolidation Records\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"Operation Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Removed: {len(records)} address(es)\n\n")
                    f.write("=" * 70 + "\n")
                    f.write("Remove Consolidation Details\n")
                    f.write("=" * 70 + "\n\n")

                    for i, record in enumerate(records, 1):
                        f.write(f"[{i}] Address:\n")
                        f.write(f"    {record['address']}\n\n")
                        f.write(f"    Operation ID: {record['consolidation_id']}\n")
                        f.write(f"    Timestamp: {record['timestamp']}\n\n")
                        f.write("-" * 70 + "\n\n")

                    f.write("=" * 70 + "\n")
                    f.write("IMPORTANT NOTES:\n")
                    f.write("=" * 70 + "\n\n")
                    f.write("• Consolidations have been removed. Rewards will now\n")
                    f.write("  be assigned to their original addresses.\n\n")
                    f.write("• Rewards are earned after mining period ends.\n\n")
                    f.write("• You must redeem rewards separately.\n\n")
                    f.write("• Keep this record for your reference.\n\n")
                else:
                    f.write("NIGHT Miner - Consolidation Records\n")
                    f.write("=" * 70 + "\n\n")
                    f.write(f"Consolidation Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Destination Address: {self.destination}\n")
                    f.write(f"Total Consolidated: {len(records)} address(es)\n\n")
                    f.write("=" * 70 + "\n")
                    f.write("Consolidation Details\n")
                    f.write("=" * 70 + "\n\n")

                    for i, record in enumerate(records, 1):
                        f.write(f"[{i}] Origin Address:\n")
                        f.write(f"    {record['origin_address']}\n\n")
                        f.write(f"    Consolidation ID: {record['consolidation_id']}\n")
                        f.write(f"    Timestamp: {record['timestamp']}\n\n")
                        f.write("-" * 70 + "\n\n")

                    f.write("=" * 70 + "\n")
                    f.write("IMPORTANT NOTES:\n")
                    f.write("=" * 70 + "\n\n")
                    f.write("• All current and future rewards from the origin addresses will\n")
                    f.write("  be assigned to the destination address.\n\n")
                    f.write("• Rewards are earned after mining period ends.\n\n")
                    f.write("• You must redeem rewards separately at the destination address.\n\n")
                    f.write("• Keep this record for your reference.\n\n")

            return txt_path  # Return the text file path as it's more user-friendly
        return None

    def process_address(self, addr: Address) -> ConsolidationResult:
        """Process a single address for consolidation or removal."""
        # Check registration
        is_registered, reg_msg, _ = self.api_client.check_registration(
            addr.address
        )

        if not is_registered:
            print(f"  ⚠️ Skipped - {reg_msg}")
            return ConsolidationResult(
                index=addr.index,
                address=addr.address,
                success=False,
                message=reg_msg,
                skipped_reason="not_registered"
            )

        try:
            # Determine destination based on operation mode
            if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
                destination = addr.address  # Same as origin to remove consolidation
            else:
                destination = self.destination

            # Sign message
            print("  Signing message...")
            signature = self.wallet_manager.sign_message(
                destination, addr
            )

            # Consolidate or remove
            if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
                print("  Removing consolidation...")
            else:
                print("  Consolidating...")

            result = self.api_client.consolidate_solutions(
                destination, addr.address, signature
            )
            result.index = addr.index

            if result.success:
                if result.donation_id:
                    print(f"  ✅ {result.message} (ID: {result.donation_id})")
                else:
                    print(f"  ✅ {result.message}")
            else:
                print(f"  ❌ {result.message}")

            return result

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return ConsolidationResult(
                index=addr.index,
                address=addr.address,
                success=False,
                message=str(e),
                skipped_reason="error"
            )

    def execute_consolidation_with_retry(self):
        """Execute the consolidation process with retry option."""
        if self.operation_mode == OperationMode.REMOVE_CONSOLIDATIONS:
            self.ui.display_header("Executing Remove Consolidations")
        else:
            self.ui.display_header("Executing Consolidation")

        results = []

        for i, addr in enumerate(self.addresses):
            self.ui.display_progress(
                i + 1, len(self.addresses),
                f"Processing {addr.address[:40]}..."
            )

            result = self.process_address(addr)
            results.append(result)

            # Delay between operations
            if i < len(self.addresses) - 1:
                time.sleep(CONFIG["api_call_delay"])

        # Save records
        record_file = self.save_consolidation_records(results)

        # Display summary
        self.ui.display_summary(results, record_file)

        # Offer retry for failed addresses
        failed = [r for r in results if not r.success and r.skipped_reason not in ["not_registered", "api_unavailable"]]

        if failed:
            print("\n" + "=" * 70)
            print("  Retry Failed Addresses".center(70))
            print("=" * 70)

            if self.ui.prompt_confirmation(f"\n{len(failed)} address(es) failed. Would you like to retry"):
                self.retry_failed_addresses(failed, results)

        # Offer undo option for successful consolidations (not for remove operations)
        if self.operation_mode == OperationMode.CONSOLIDATE:
            successful = [r for r in results if r.success]
            if successful:
                print("\n" + "=" * 70)
                print("  Undo Consolidation".center(70))
                print("=" * 70)
                print("\nYou can undo this consolidation, which will remove the reward assignment")
                print("and return rewards to their original addresses.")

                if self.ui.prompt_confirmation("\nWould you like to undo this consolidation"):
                    self.undo_consolidation(results)

    def retry_failed_addresses(self, failed_results: List[ConsolidationResult], all_results: List[ConsolidationResult]):
        """Retry failed addresses."""
        self.ui.display_header("Retrying Failed Addresses")

        retry_addresses = []
        for r in failed_results:
            for addr in self.addresses:
                if addr.index == r.index:
                    retry_addresses.append(addr)
                    break

        new_results = []
        for i, addr in enumerate(retry_addresses):
            self.ui.display_progress(
                i + 1, len(retry_addresses),
                f"Retrying {addr.address[:40]}..."
            )

            result = self.process_address(addr)
            new_results.append(result)

            # Update the original results
            for j, orig_result in enumerate(all_results):
                if orig_result.index == result.index:
                    all_results[j] = result
                    break

            if i < len(retry_addresses) - 1:
                time.sleep(CONFIG["api_call_delay"])

        # Save updated records
        record_file = self.save_consolidation_records(all_results)

        # Display updated summary
        self.ui.display_summary(all_results, record_file)

        # Check if there are still failures
        still_failed = [r for r in new_results if not r.success and r.skipped_reason not in ["not_registered", "api_unavailable"]]

        if still_failed:
            if self.ui.prompt_confirmation(f"\n{len(still_failed)} address(es) still failed. Retry again"):
                self.retry_failed_addresses(still_failed, all_results)
        else:
            if new_results:  # Only show success message if we actually retried something
                print("\n✅ All retried addresses processed successfully!")

    def undo_consolidation(self, original_results: List[ConsolidationResult]):
        """Undo a consolidation by removing assignments (origin = destination)."""
        self.ui.display_header("Undoing Consolidation")

        # Get addresses that were successfully consolidated
        successful_consolidations = [r for r in original_results if r.success]

        if not successful_consolidations:
            print("No successful consolidations to undo.")
            return

        print(f"Undoing {len(successful_consolidations)} consolidation(s)...\n")

        undo_results = []

        for i, orig_result in enumerate(successful_consolidations):
            # Find the corresponding address
            addr = None
            for a in self.addresses:
                if a.index == orig_result.index:
                    addr = a
                    break

            if not addr:
                continue

            self.ui.display_progress(
                i + 1, len(successful_consolidations),
                f"Undoing {addr.address[:40]}..."
            )

            try:
                # Sign message with origin = destination (same address)
                print("  Signing message...")
                signature = self.wallet_manager.sign_message(
                    addr.address, addr
                )

                # Call API with origin = destination to undo
                print("  Removing consolidation...")
                result = self.api_client.consolidate_solutions(
                    addr.address, addr.address, signature
                )
                result.index = addr.index

                if result.success:
                    if result.donation_id:
                        print(f"  ✅ {result.message} (ID: {result.donation_id})")
                    else:
                        print(f"  ✅ {result.message}")
                else:
                    print(f"  ❌ {result.message}")

                undo_results.append(result)

            except Exception as e:
                print(f"  ❌ Error: {e}")
                undo_results.append(ConsolidationResult(
                    index=addr.index,
                    address=addr.address,
                    success=False,
                    message=str(e),
                    skipped_reason="error"
                ))

            # Delay between operations
            if i < len(successful_consolidations) - 1:
                time.sleep(CONFIG["api_call_delay"])

        # Display summary
        print("\n" + "=" * 70)
        print("  Undo Summary".center(70))
        print("=" * 70)

        successful_undos = [r for r in undo_results if r.success]
        failed_undos = [r for r in undo_results if not r.success]

        print(f"\nTotal undos attempted: {len(undo_results)}")
        print(f"Successful:            {len(successful_undos)}")
        print(f"Failed:                {len(failed_undos)}")

        if successful_undos:
            print("\nSuccessfully undone:")
            for r in successful_undos:
                if r.donation_id:
                    print(f"  ✅ [{r.index}] {r.address[:40]}...")
                    print(f"     ID: {r.donation_id}")
                else:
                    print(f"  ✅ [{r.index}] {r.address[:40]}...")

        if failed_undos:
            print("\nFailed to undo:")
            for r in failed_undos:
                print(f"  ❌ [{r.index}] {r.address[:40]}...")
                print(f"     Reason: {r.message}")

        print("\n" + "=" * 70)


# ==============================================================================
# Entry Point
# ==============================================================================

def main():
    """Main entry point."""
    controller = ConsolidationController()
    controller.run()


if __name__ == "__main__":
    main()
