#!/usr/bin/env python3
# ==============================================================================
# Night Miner Token Redeemer
#
# If you mined NIGHT tokens but didn't consolidate your mining wallet before
# the airdrop snapshot, you're stuck with hundreds of separate addresses.
# Normally you'd have to import each key into Eternl and redeem manually,
# one address at a time.
#
# This tool automates that entire process:
# - Checks which addresses have redeemable tokens
# - Batch redeems tokens across all your mining addresses
# - Consolidates everything to a single wallet you control
#
# For help, see the README.md file or contact the developer.
# ==============================================================================

import os
import sys
import json
import time
import logging
import re
import hashlib
import webbrowser
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

# Setup logging FIRST (before any other imports that might log)
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "night_redeemer.log")

# Create logs directory if needed
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create logger - file only, never console
logger = logging.getLogger("night_redeemer")
logger.setLevel(logging.DEBUG)

# Remove any existing handlers
logger.handlers = []

# File handler only
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
logger.addHandler(file_handler)

# Prevent propagation to root logger (which might have console handlers)
logger.propagate = False

logger.info("=" * 60)
logger.info("Night Miner Token Redeemer starting")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")


# ==============================================================================
# Cardano Library Import
# ==============================================================================

try:
    from pycardano import (
        PaymentSigningKey,
        PaymentVerificationKey,
        Address,
        Network,
        Transaction,
        TransactionWitnessSet,
        VerificationKeyWitness,
        TransactionBuilder,
        TransactionOutput,
        Value,
        MultiAsset,
        Asset,
        AssetName,
        ScriptHash,
        BlockFrostChainContext,
    )
    import cbor2
    PYCARDANO_AVAILABLE = True
    logger.info("pycardano library loaded successfully")
except ImportError as e:
    PYCARDANO_AVAILABLE = False
    logger.error(f"pycardano import failed: {e}")
except Exception as e:
    PYCARDANO_AVAILABLE = False
    logger.error(f"pycardano load error: {type(e).__name__}: {e}")

# Optional tkinter for folder selection
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
    logger.info("tkinter available for folder selection")
except ImportError:
    TKINTER_AVAILABLE = False
    logger.info("tkinter not available - will use manual path entry")


# ==============================================================================
# Configuration
# ==============================================================================

VERSION = "1.0.0"

CONFIG_FILE = "night_redeemer_config.json"
THAW_DATA_FILE = "thaw_schedules.json"

# API endpoints
MIDNIGHT_API_BASE = "https://mainnet.prod.gd.midnighttge.io"
BLOCKFROST_API_BASE = "https://cardano-mainnet.blockfrost.io/api/v0"

# Delays (seconds)
API_CALL_DELAY = 2
BATCH_DELAY = 5

# ADA thresholds (lovelace)
MIN_BALANCE_TO_START = 5_000_000  # 5 ADA
MIN_BALANCE_PER_REDEMPTION = 3_500_000  # ~3.5 ADA (conservative estimate for balance check)
MIN_BALANCE_PER_CONSOLIDATION = 2_000_000  # ~2 ADA

# NIGHT token identifiers
NIGHT_POLICY_ID = "0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa"
NIGHT_ASSET_NAME = "4e49474854"  # "NIGHT" in hex


# ==============================================================================
# Data Classes
# ==============================================================================

DEFAULT_WALLET_DIR = "mining-wallet"
DEFAULT_FEE_WALLET_DIR = "fee-wallet"


@dataclass
class Config:
    """Application configuration."""
    wallet_dir: str = ""
    blockfrost_api_key: str = ""
    fee_wallet_dir: str = DEFAULT_FEE_WALLET_DIR

    def save(self):
        """Save config to file."""
        data = {
            "wallet_dir": self.wallet_dir,
            "blockfrost_api_key": self.blockfrost_api_key,
            "fee_wallet_dir": self.fee_wallet_dir,
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Config saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    @classmethod
    def load(cls) -> 'Config':
        """Load config from file."""
        config = cls()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                config.wallet_dir = data.get("wallet_dir", "")
                config.blockfrost_api_key = data.get("blockfrost_api_key", "")
                config.fee_wallet_dir = data.get("fee_wallet_dir", "fee-wallet")
                logger.info(f"Config loaded from {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return config


@dataclass
class WalletAddress:
    """A mining wallet address."""
    index: int
    address: str
    addr_file: Path
    skey_file: Path


@dataclass
class UTxO:
    """A Cardano UTxO."""
    tx_hash: str
    tx_index: int
    address: str
    amount: int  # lovelace

    def to_cbor_hex(self) -> str:
        """Encode for Midnight API."""
        tx_input = [bytes.fromhex(self.tx_hash), self.tx_index]
        addr = Address.from_primitive(self.address)
        addr_bytes = bytes(addr.to_primitive())
        tx_output = [addr_bytes, self.amount]
        utxo_data = [tx_input, tx_output]
        return cbor2.dumps(utxo_data).hex()


@dataclass
class BatchResult:
    """Result of a batch operation."""
    address: str
    success: bool
    message: str
    tx_id: Optional[str] = None
    amount: Optional[int] = None
    skey_file: Optional[str] = None


# ==============================================================================
# Utility Functions
# ==============================================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_ada(lovelace: int) -> str:
    """Format lovelace as ADA."""
    return f"{lovelace / 1_000_000:,.6f} ADA"


def format_night(star: int) -> str:
    """Format STAR as NIGHT."""
    return f"{star / 1_000_000:,.6f} NIGHT"


def format_night_short(star: int) -> str:
    """Format STAR as NIGHT (shorter)."""
    night = star / 1_000_000
    if night >= 1000:
        return f"{night:,.2f}"
    return f"{night:,.6f}"


def truncate_address(addr: str, length: int = 35) -> str:
    """Truncate address for display."""
    if len(addr) <= length:
        return addr
    return addr[:length] + "..."


# ==============================================================================
# Logging HTTP Client Wrapper
# ==============================================================================

class LoggingSession:
    """HTTP session wrapper that logs all requests and responses."""

    def __init__(self, name: str = "HTTP"):
        self.session = requests.Session()
        self.name = name

    def _log_request(self, method: str, url: str, **kwargs):
        """Log outgoing request."""
        logger.debug(f"{self.name} REQUEST: {method} {url}")
        if 'headers' in kwargs:
            # Don't log sensitive headers fully
            headers = {k: (v[:20] + "..." if k.lower() == "project_id" else v)
                      for k, v in kwargs['headers'].items()}
            logger.debug(f"{self.name} Headers: {headers}")
        if 'json' in kwargs:
            # Truncate large payloads
            payload = str(kwargs['json'])
            if len(payload) > 500:
                payload = payload[:500] + "..."
            logger.debug(f"{self.name} Payload: {payload}")

    def _log_response(self, response: requests.Response):
        """Log incoming response."""
        logger.debug(f"{self.name} RESPONSE: {response.status_code} {response.reason}")
        # Truncate large responses
        text = response.text
        if len(text) > 1000:
            text = text[:1000] + "..."
        logger.debug(f"{self.name} Body: {text}")

    def get(self, url: str, **kwargs) -> requests.Response:
        self._log_request("GET", url, **kwargs)
        try:
            response = self.session.get(url, **kwargs)
            self._log_response(response)
            return response
        except Exception as e:
            logger.error(f"{self.name} GET error: {e}")
            raise

    def post(self, url: str, **kwargs) -> requests.Response:
        self._log_request("POST", url, **kwargs)
        try:
            response = self.session.post(url, **kwargs)
            self._log_response(response)
            return response
        except Exception as e:
            logger.error(f"{self.name} POST error: {e}")
            raise

    def update_headers(self, headers: dict):
        self.session.headers.update(headers)


# ==============================================================================
# Fee Wallet
# ==============================================================================

class FeeWallet:
    """Manages the fee wallet for transaction fees."""

    def __init__(self, wallet_dir: str):
        self.wallet_dir = Path(wallet_dir)
        self.skey_path = self.wallet_dir / "fee-wallet.skey"
        self.vkey_path = self.wallet_dir / "fee-wallet.vkey"
        self.addr_path = self.wallet_dir / "fee-wallet.addr"

        self.signing_key: Optional[PaymentSigningKey] = None
        self.verification_key: Optional[PaymentVerificationKey] = None
        self.address: Optional[Address] = None

        logger.debug(f"FeeWallet initialized: {wallet_dir}")

    def exists(self) -> bool:
        exists = self.skey_path.exists() and self.addr_path.exists()
        logger.debug(f"FeeWallet exists: {exists}")
        return exists

    def generate(self) -> str:
        """Generate new fee wallet."""
        logger.info("Generating new fee wallet")
        self.wallet_dir.mkdir(parents=True, exist_ok=True)

        self.signing_key = PaymentSigningKey.generate()
        self.verification_key = PaymentVerificationKey.from_signing_key(self.signing_key)
        self.address = Address(payment_part=self.verification_key.hash(), network=Network.MAINNET)

        # Save keys
        skey_data = {
            "type": "PaymentSigningKeyShelley_ed25519",
            "description": "Fee Wallet Signing Key",
            "cborHex": "5820" + self.signing_key.payload.hex()
        }
        with open(self.skey_path, 'w') as f:
            json.dump(skey_data, f, indent=2)

        vkey_data = {
            "type": "PaymentVerificationKeyShelley_ed25519",
            "description": "Fee Wallet Verification Key",
            "cborHex": "5820" + self.verification_key.payload.hex()
        }
        with open(self.vkey_path, 'w') as f:
            json.dump(vkey_data, f, indent=2)

        with open(self.addr_path, 'w') as f:
            f.write(str(self.address))

        # Add README explaining the fee wallet
        readme_path = self.wallet_dir / "README.txt"
        if not readme_path.exists():
            readme_content = f"""================================================================================
                           FEE WALLET
================================================================================

This is your fee wallet for the Night Miner Token Redeemer.

ADDRESS:
  {self.address}

Send ADA to this address to pay for transaction fees.


FILES IN THIS FOLDER:
---------------------
  fee-wallet.addr  - The wallet address (safe to share)
  fee-wallet.vkey  - Public verification key (safe to share)
  fee-wallet.skey  - PRIVATE signing key (KEEP SECRET!)


IMPORTANT - BACKUP YOUR .skey FILE!
-----------------------------------
The fee-wallet.skey file is your private key. If you lose it, you lose
access to any ADA in this wallet. Back it up securely.


COSTS:
------
  Redeeming tokens:   ~3.25 ADA per mining address
  Consolidating:      ~0.5 ADA per address (offset by mining address ADA)

Recommended: Keep 5-10 ADA in this wallet to start.

================================================================================
"""
            with open(readme_path, 'w') as f:
                f.write(readme_content)

        logger.info(f"Fee wallet created: {self.address}")
        return str(self.address)

    def load(self) -> str:
        """Load existing fee wallet."""
        logger.debug("Loading fee wallet")
        with open(self.skey_path, 'r') as f:
            skey_data = json.load(f)

        cbor_hex = skey_data["cborHex"]
        key_hex = cbor_hex[4:] if cbor_hex.startswith("5820") else cbor_hex

        self.signing_key = PaymentSigningKey.from_primitive(bytes.fromhex(key_hex))
        self.verification_key = PaymentVerificationKey.from_signing_key(self.signing_key)

        with open(self.addr_path, 'r') as f:
            addr_str = f.read().strip()
        self.address = Address.from_primitive(addr_str)

        logger.debug(f"Fee wallet loaded: {self.address}")
        return str(self.address)

    def get_address(self) -> str:
        if self.address is None:
            self.load()
        return str(self.address)


# ==============================================================================
# Blockfrost Client
# ==============================================================================

class BlockfrostClient:
    """Client for Blockfrost API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = BLOCKFROST_API_BASE
        self.session = LoggingSession("Blockfrost")
        self.session.update_headers({"project_id": api_key})
        logger.info("BlockfrostClient initialized")

    def test_connection(self) -> bool:
        """Test API connection."""
        logger.info("Testing Blockfrost connection")
        try:
            response = self.session.get(f"{self.base_url}/blocks/latest", timeout=10)
            response.raise_for_status()
            logger.info("Blockfrost connection OK")
            return True
        except Exception as e:
            logger.error(f"Blockfrost connection failed: {e}")
            return False

    def get_address_utxos(self, address: str) -> List[UTxO]:
        """Get UTxOs for an address."""
        logger.debug(f"Getting UTxOs for {truncate_address(address)}")
        url = f"{self.base_url}/addresses/{address}/utxos"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                logger.debug("No UTxOs found (404)")
                return []
            response.raise_for_status()

            utxos = []
            for item in response.json():
                lovelace = 0
                for amount in item.get("amount", []):
                    if amount["unit"] == "lovelace":
                        lovelace = int(amount["quantity"])
                        break
                if lovelace > 0:
                    utxos.append(UTxO(
                        tx_hash=item["tx_hash"],
                        tx_index=item["tx_index"],
                        address=address,
                        amount=lovelace
                    ))
            logger.debug(f"Found {len(utxos)} UTxOs, total {sum(u.amount for u in utxos)} lovelace")
            return utxos
        except Exception as e:
            logger.error(f"Failed to get UTxOs: {e}")
            return []

    def get_address_balance(self, address: str) -> int:
        """Get ADA balance in lovelace."""
        return sum(utxo.amount for utxo in self.get_address_utxos(address))

    def get_address_utxos_with_assets(self, address: str) -> List[Dict]:
        """Get UTxOs including native assets."""
        logger.debug(f"Getting UTxOs with assets for {truncate_address(address)}")
        url = f"{self.base_url}/addresses/{address}/utxos"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return []
            response.raise_for_status()

            utxos = []
            for item in response.json():
                utxo = {
                    "tx_hash": item["tx_hash"],
                    "tx_index": item["tx_index"],
                    "address": address,
                    "lovelace": 0,
                    "assets": []
                }
                for amount in item.get("amount", []):
                    if amount["unit"] == "lovelace":
                        utxo["lovelace"] = int(amount["quantity"])
                    else:
                        unit = amount["unit"]
                        utxo["assets"].append({
                            "policy_id": unit[:56],
                            "asset_name_hex": unit[56:],
                            "quantity": int(amount["quantity"])
                        })
                utxos.append(utxo)
            return utxos
        except Exception as e:
            logger.error(f"Failed to get UTxOs with assets: {e}")
            return []

    def submit_transaction(self, tx_cbor: bytes) -> Optional[str]:
        """Submit signed transaction."""
        logger.info("Submitting transaction to Blockfrost")
        url = f"{self.base_url}/tx/submit"
        try:
            # Don't use LoggingSession for binary data
            response = self.session.session.post(
                url, data=tx_cbor,
                headers={"Content-Type": "application/cbor"},
                timeout=60
            )
            logger.debug(f"Submit response: {response.status_code} {response.text[:200]}")
            response.raise_for_status()
            tx_hash = response.text.strip('"')
            logger.info(f"Transaction submitted: {tx_hash}")
            return tx_hash
        except requests.exceptions.HTTPError as e:
            logger.error(f"Submit failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return None


# ==============================================================================
# Midnight Client
# ==============================================================================

class MidnightClient:
    """Client for Midnight TGE API."""

    def __init__(self):
        self.base_url = MIDNIGHT_API_BASE
        self.session = LoggingSession("Midnight")
        self.session.update_headers({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://tge.midnight.network",
            "Referer": "https://tge.midnight.network/",
        })
        logger.info("MidnightClient initialized")

    def get_thaw_schedule(self, address: str) -> Optional[Dict]:
        """Get thaw schedule for address."""
        logger.debug(f"Getting thaw schedule for {truncate_address(address)}")
        url = f"{self.base_url}/thaws/{address}/schedule"
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                logger.debug("No schedule found (404)")
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get schedule: {e}")
            return None

    def build_redemption_transaction(self, mining_address: str, change_address: str,
                                     funding_utxos: List[UTxO]) -> Optional[Dict]:
        """Build redemption transaction."""
        logger.info(f"Building redemption tx for {truncate_address(mining_address)}")
        url = f"{self.base_url}/thaws/{mining_address}/transactions/build"

        payload = {
            "change_address": change_address,
            "funding_utxos": [utxo.to_cbor_hex() for utxo in funding_utxos],
            "collateral_utxos": []
        }

        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Transaction built: {result.get('transaction_id', 'unknown')}")
            return result
        except requests.exceptions.HTTPError as e:
            logger.error(f"Build failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Build error: {e}")
            return None

    def submit_transaction(self, mining_address: str, transaction_cbor: str,
                          witness_set_cbor: str) -> Optional[Dict]:
        """Submit signed redemption transaction."""
        logger.info(f"Submitting redemption tx for {truncate_address(mining_address)}")
        url = f"{self.base_url}/thaws/{mining_address}/transactions"

        payload = {
            "transaction": transaction_cbor,
            "transaction_witness_set": witness_set_cbor
        }

        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Redemption submitted successfully")
            return result
        except requests.exceptions.HTTPError as e:
            logger.error(f"Submit failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return None


# ==============================================================================
# Transaction Signing
# ==============================================================================

def load_signing_key_from_file(skey_path: str) -> PaymentSigningKey:
    """Load signing key from .skey file."""
    logger.debug(f"Loading signing key from {skey_path}")
    with open(skey_path, 'r') as f:
        skey_data = json.load(f)

    cbor_hex = skey_data["cborHex"]
    key_hex = cbor_hex[4:] if cbor_hex.startswith("5820") else cbor_hex
    return PaymentSigningKey.from_primitive(bytes.fromhex(key_hex))


def sign_with_key(tx_cbor_hex: str, signing_key: PaymentSigningKey,
                  tx_id_from_server: str = None) -> str:
    """Sign transaction and return witness set CBOR hex."""
    logger.debug("Signing transaction")

    if tx_id_from_server:
        tx_body_hash = bytes.fromhex(tx_id_from_server)
        logger.debug(f"Using server tx_id as hash: {tx_id_from_server[:16]}...")
    else:
        tx_bytes = bytes.fromhex(tx_cbor_hex)
        tx_array = cbor2.loads(tx_bytes)
        tx_body = tx_array[0]
        tx_body_cbor = cbor2.dumps(tx_body)
        tx_body_hash = hashlib.blake2b(tx_body_cbor, digest_size=32).digest()
        logger.debug(f"Computed tx hash: {tx_body_hash.hex()[:16]}...")

    verification_key = PaymentVerificationKey.from_signing_key(signing_key)
    signature = signing_key.sign(tx_body_hash)

    vkey_witness = VerificationKeyWitness(vkey=verification_key, signature=signature)
    witness_set = TransactionWitnessSet()
    witness_set.vkey_witnesses = [vkey_witness]

    logger.debug("Transaction signed")
    return witness_set.to_cbor().hex()


# ==============================================================================
# Wallet Operations
# ==============================================================================

def find_wallet_addresses(wallet_dir: str) -> List[WalletAddress]:
    """Find all address files in wallet directory."""
    logger.debug(f"Scanning for addresses in {wallet_dir}")
    wallet_path = Path(wallet_dir)
    addresses = []

    for addr_file in sorted(wallet_path.glob("addr-*.addr")):
        match = re.match(r"addr-(\d+)\.addr", addr_file.name)
        if match:
            index = int(match.group(1))
            skey_file = wallet_path / f"addr-{index}.skey"

            if skey_file.exists():
                with open(addr_file, 'r') as f:
                    address_str = f.read().strip()

                addresses.append(WalletAddress(
                    index=index,
                    address=address_str,
                    addr_file=addr_file,
                    skey_file=skey_file
                ))

    logger.info(f"Found {len(addresses)} wallet addresses")
    return addresses


def find_skey_path(skey_file: str, skey_dir: str = None) -> Optional[str]:
    """Find signing key file."""
    search_paths = [
        skey_file,
        os.path.join(skey_dir or ".", skey_file),
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None


# ==============================================================================
# Thaw Schedule Operations
# ==============================================================================

def load_thaw_data(wallet_dir: str) -> Dict:
    """Load thaw schedules from file."""
    data_file = os.path.join(wallet_dir, THAW_DATA_FILE)
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load thaw data: {e}")
    return {"last_full_refresh": None, "addresses": {}}


def save_thaw_data(wallet_dir: str, data: Dict):
    """Save thaw schedules to file."""
    data_file = os.path.join(wallet_dir, THAW_DATA_FILE)
    try:
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Thaw data saved to {data_file}")
    except Exception as e:
        logger.error(f"Failed to save thaw data: {e}")


def get_thaw_summary(thaw_data: Dict) -> Dict:
    """Calculate summary statistics from thaw data."""
    total_redeemable = 0
    total_upcoming = 0
    redeemable_count = 0
    upcoming_by_date = {}

    for addr, data in thaw_data.get("addresses", {}).items():
        if data.get("failed"):
            continue

        for thaw in data.get("thaws", []):
            amount = thaw.get("amount", 0)
            status = thaw.get("status", "")

            if status == "redeemable":
                total_redeemable += amount
                redeemable_count += 1
            elif status == "upcoming":
                total_upcoming += amount
                date_key = thaw.get("thawing_period_start", "")[:10] or "Unknown"
                if date_key not in upcoming_by_date:
                    upcoming_by_date[date_key] = 0
                upcoming_by_date[date_key] += amount

    return {
        "total_redeemable": total_redeemable,
        "redeemable_count": redeemable_count,
        "total_upcoming": total_upcoming,
        "upcoming_by_date": upcoming_by_date,
    }


def get_redeemable_addresses(thaw_data: Dict) -> List[Dict]:
    """Get list of addresses with redeemable tokens."""
    redeemable = []
    for address, data in thaw_data.get("addresses", {}).items():
        if data.get("failed"):
            continue

        thaws = data.get("thaws", [])
        redeemable_thaws = [t for t in thaws if t.get("status") == "redeemable"]

        if redeemable_thaws:
            total = sum(t.get("amount", 0) for t in redeemable_thaws)
            redeemable.append({
                "address": address,
                "amount": total,
                "skey_file": data.get("skey_file"),
                "key_index": data.get("key_index"),
            })

    return redeemable


# ==============================================================================
# Batch Operations
# ==============================================================================

def redeem_single(mining_address: str, skey_file: str, wallet_dir: str,
                  fee_wallet: FeeWallet, blockfrost: BlockfrostClient,
                  midnight: MidnightClient) -> BatchResult:
    """Redeem tokens for single address."""
    logger.info(f"Redeeming for {skey_file}")

    skey_path = find_skey_path(skey_file, wallet_dir)
    if not skey_path:
        logger.error(f"Key not found: {skey_file}")
        return BatchResult(mining_address, False, f"Key not found: {skey_file}", skey_file=skey_file)

    fee_address = fee_wallet.get_address()
    utxos = blockfrost.get_address_utxos(fee_address)
    if not utxos:
        logger.error("No UTxOs in fee wallet")
        return BatchResult(mining_address, False, "No UTxOs in fee wallet", skey_file=skey_file)

    print(f"    Building...", end=" ", flush=True)
    build_result = midnight.build_redemption_transaction(mining_address, fee_address, utxos)
    if not build_result:
        return BatchResult(mining_address, False, "Build failed", skey_file=skey_file)

    tx_cbor = build_result.get("transaction")
    tx_id = build_result.get("transaction_id")
    redeemed_amount = build_result.get("redeemed_amount", 0)

    print(f"signing...", end=" ", flush=True)
    try:
        if fee_wallet.signing_key is None:
            fee_wallet.load()
        witness_set = sign_with_key(tx_cbor, fee_wallet.signing_key, tx_id_from_server=tx_id)
    except Exception as e:
        logger.error(f"Sign failed: {e}")
        return BatchResult(mining_address, False, f"Sign failed: {e}", skey_file=skey_file)

    print(f"submitting...", end=" ", flush=True)
    submit_result = midnight.submit_transaction(mining_address, tx_cbor, witness_set)

    if submit_result is None:
        return BatchResult(mining_address, False, "Submit failed", tx_id=tx_id, skey_file=skey_file)

    return BatchResult(
        mining_address, True, "Success",
        tx_id=tx_id, amount=redeemed_amount, skey_file=skey_file
    )


def consolidate_single(source_address: str, destination_address: str, skey_path: str,
                       fee_wallet: FeeWallet, blockfrost: BlockfrostClient) -> BatchResult:
    """Consolidate NIGHT from single address."""
    logger.info(f"Consolidating from {truncate_address(source_address)}")

    source_utxos = blockfrost.get_address_utxos_with_assets(source_address)
    if not source_utxos:
        return BatchResult(source_address, False, "No UTxOs at source")

    total_lovelace = sum(u["lovelace"] for u in source_utxos)
    total_night = 0
    for utxo in source_utxos:
        for asset in utxo["assets"]:
            if asset["policy_id"] == NIGHT_POLICY_ID:
                total_night += asset["quantity"]

    if total_night == 0:
        return BatchResult(source_address, False, "No NIGHT tokens")

    print(f"    {format_ada(total_lovelace)} + {format_night(total_night)}")

    try:
        source_skey = load_signing_key_from_file(skey_path)
        if fee_wallet.signing_key is None:
            fee_wallet.load()
    except Exception as e:
        logger.error(f"Key load failed: {e}")
        return BatchResult(source_address, False, f"Key load failed: {e}")

    print(f"    Building...", end=" ", flush=True)
    try:
        context = BlockFrostChainContext(project_id=blockfrost.api_key, network=Network.MAINNET)
        builder = TransactionBuilder(context)

        source_addr = Address.from_primitive(source_address)
        fee_addr = Address.from_primitive(fee_wallet.get_address())
        dest_addr = Address.from_primitive(destination_address)

        builder.add_input_address(source_addr)
        builder.add_input_address(fee_addr)

        policy_id = ScriptHash.from_primitive(bytes.fromhex(NIGHT_POLICY_ID))
        asset_name = AssetName(bytes.fromhex(NIGHT_ASSET_NAME))

        multi_asset = MultiAsset()
        multi_asset[policy_id] = Asset()
        multi_asset[policy_id][asset_name] = total_night

        output_value = Value(1_500_000, multi_asset)
        builder.add_output(TransactionOutput(dest_addr, output_value))

        signed_tx = builder.build_and_sign(
            signing_keys=[source_skey, fee_wallet.signing_key],
            change_address=fee_addr
        )

        print(f"submitting...", end=" ", flush=True)
        tx_hash = blockfrost.submit_transaction(signed_tx.to_cbor())

        if tx_hash:
            logger.info(f"Consolidation successful: {tx_hash}")
            return BatchResult(source_address, True, "Success", tx_id=tx_hash, amount=total_night)
        else:
            return BatchResult(source_address, False, "Submit failed")

    except Exception as e:
        logger.error(f"Consolidation failed: {e}", exc_info=True)
        print(f"FAILED")
        return BatchResult(source_address, False, f"Build failed: {e}")


def drain_fee_wallet(destination_address: str, fee_wallet: FeeWallet,
                     blockfrost: BlockfrostClient) -> BatchResult:
    """Send all remaining ADA from fee wallet to destination."""
    logger.info(f"Draining fee wallet to {truncate_address(destination_address)}")

    fee_address = fee_wallet.get_address()
    balance = blockfrost.get_address_balance(fee_address)

    # Need enough for min UTxO (~1 ADA) plus fee (~0.2 ADA)
    MIN_FOR_DRAIN = 1_200_000  # 1.2 ADA minimum to attempt drain
    if balance < MIN_FOR_DRAIN:
        return BatchResult(fee_address, False, f"Balance too low to drain: {format_ada(balance)}")

    try:
        if fee_wallet.signing_key is None:
            fee_wallet.load()
    except Exception as e:
        logger.error(f"Key load failed: {e}")
        return BatchResult(fee_address, False, f"Key load failed: {e}")

    print(f"    Building...", end=" ", flush=True)
    try:
        context = BlockFrostChainContext(
            project_id=blockfrost.api_key,
            base_url="https://cardano-mainnet.blockfrost.io/api"
        )
        builder = TransactionBuilder(context)

        fee_addr = Address.from_primitive(fee_address)
        dest_addr = Address.from_primitive(destination_address)

        builder.add_input_address(fee_addr)

        # Don't add explicit output - let all funds go as "change" to destination
        # This avoids the issue of small leftover change being below min UTxO
        # The builder will create a single output: (total input - fee) -> destination

        signed_tx = builder.build_and_sign(
            signing_keys=[fee_wallet.signing_key],
            change_address=dest_addr  # All funds (minus fee) go here
        )

        # Calculate what was actually sent (balance minus fee)
        actual_sent = balance - signed_tx.transaction_body.fee

        print(f"submitting...", end=" ", flush=True)
        tx_hash = blockfrost.submit_transaction(signed_tx.to_cbor())

        if tx_hash:
            logger.info(f"Fee wallet drained: {tx_hash}")
            return BatchResult(fee_address, True, "Success", tx_id=tx_hash, amount=actual_sent)
        else:
            return BatchResult(fee_address, False, "Submit failed")

    except Exception as e:
        logger.error(f"Fee wallet drain failed: {e}", exc_info=True)
        print(f"FAILED")
        return BatchResult(fee_address, False, f"Failed: {e}")


def save_batch_results(results: List[BatchResult], operation: str, destination: str = None):
    """Save batch results to file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{operation}_results_{timestamp}.json"

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "total": len(results),
        "successful": len([r for r in results if r.success]),
        "failed": len([r for r in results if not r.success]),
        "results": [
            {
                "address": r.address,
                "skey_file": r.skey_file,
                "success": r.success,
                "message": r.message,
                "tx_id": r.tx_id,
                "amount": r.amount
            }
            for r in results
        ]
    }

    if destination:
        data["destination"] = destination

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Results saved to {filename}")
    print(f"\nResults saved to: {filename}")


# ==============================================================================
# User Interface
# ==============================================================================

class NightManager:
    """Main application class."""

    def __init__(self):
        self.config = Config.load()
        self.thaw_data: Dict = {}
        self.fee_wallet: Optional[FeeWallet] = None
        self.blockfrost: Optional[BlockfrostClient] = None
        self.midnight: Optional[MidnightClient] = None

    def setup_required(self) -> bool:
        """Check if initial setup is needed."""
        # Check if we have a configured wallet dir that exists
        if self.config.wallet_dir and os.path.isdir(self.config.wallet_dir):
            wallet_ok = True
        # Or check if the default mining-wallet dir exists with keys
        elif os.path.isdir(DEFAULT_WALLET_DIR) and find_wallet_addresses(DEFAULT_WALLET_DIR):
            self.config.wallet_dir = DEFAULT_WALLET_DIR
            wallet_ok = True
        else:
            wallet_ok = False

        return not wallet_ok or not self.config.blockfrost_api_key

    def run_setup(self):
        """Run first-time setup wizard."""
        clear_screen()
        print("=" * 55)
        print("      Night Miner Token Redeemer - First Time Setup")
        print("=" * 55)
        print("\nWelcome! Let's get you set up.\n")
        logger.info("Running first-time setup")

        # Step 1: Wallet directory
        print("STEP 1: Mining Wallet Location")
        print("-" * 55)
        print("Where is your mining wallet folder?")
        print("(Contains addr-0.addr, addr-0.skey, etc.)\n")

        # Default to mining-wallet subfolder
        default_wallet = os.path.join(os.getcwd(), "mining-wallet")

        if TKINTER_AVAILABLE:
            print(f"Default: {default_wallet}")
            print("")
            print("[1] Use default (mining-wallet folder)")
            print("[2] Browse for a different folder")
            print("")
            choice = input("Choice [1]: ").strip()

            if choice == "2":
                root = tk.Tk()
                root.withdraw()
                wallet_dir = filedialog.askdirectory(title="Select your mining wallet folder")
                if not wallet_dir:
                    print("\nNo folder selected.")
                    input("\nPress Enter to try again...")
                    return
            else:
                wallet_dir = default_wallet
        else:
            print(f"Default: {default_wallet}")
            print("")
            print("Press Enter to use default, or type a different path:")
            user_input = input("> ").strip()
            wallet_dir = user_input if user_input else default_wallet

        if not os.path.isdir(wallet_dir):
            # Create the default folder if it doesn't exist
            if wallet_dir == default_wallet:
                os.makedirs(wallet_dir, exist_ok=True)
                print(f"\nCreated folder: {wallet_dir}")
            else:
                print(f"\nFolder not found: {wallet_dir}")
                input("\nPress Enter to try again...")
                return

        # Verify it has wallet files
        addresses = find_wallet_addresses(wallet_dir)
        if not addresses:
            print(f"\nNo wallet files found in {wallet_dir}")
            print("Looking for addr-*.addr and addr-*.skey files.")
            print("")
            print("-" * 55)
            print("Please copy your mining wallet files to this folder:")
            print(f"  {os.path.abspath(wallet_dir)}")
            print("")
            print("You need files like:")
            print("  addr-0.addr, addr-0.skey")
            print("  addr-1.addr, addr-1.skey")
            print("  etc.")
            print("-" * 55)
            input("\nPress Enter to try again (or Ctrl+C to quit)...")
            return

        self.config.wallet_dir = wallet_dir
        print(f"\nFound {len(addresses)} wallet addresses.")
        logger.info(f"Wallet directory set: {wallet_dir}")

        # Step 2: Blockfrost API key
        print("\n" + "=" * 55)
        print("STEP 2: Blockfrost API Key")
        print("-" * 55)
        print("You need a free Blockfrost API key.\n")
        print("1. Sign up / Log in at blockfrost.io")
        print("2. Create a project (choose 'Cardano Mainnet')")
        print("3. Copy the API key\n")

        open_browser = input("Open Blockfrost website in browser? [Y/n]: ").strip().lower()
        if open_browser != 'n':
            print("\nOpening browser...")
            webbrowser.open("https://blockfrost.io/dashboard")
            print("Sign up or log in, create a project, and copy your API key.\n")

        api_key = input("Paste your API key here: ").strip()

        if not api_key:
            print("\nNo API key provided.")
            input("\nPress Enter to continue...")
            return

        # Test connection
        print("\nTesting connection...")
        test_client = BlockfrostClient(api_key)
        if not test_client.test_connection():
            print("\nConnection failed. Please check your API key.")
            input("\nPress Enter to continue...")
            return

        self.config.blockfrost_api_key = api_key
        print("Connection successful!")
        logger.info("Blockfrost API key verified")

        # Save config
        self.config.save()

        print("\n" + "=" * 55)
        print("Setup complete!")
        print("=" * 55)
        input("\nPress Enter to continue to main menu...")

    def initialize(self):
        """Initialize clients and load data."""
        logger.info("Initializing application")

        if self.config.blockfrost_api_key:
            self.blockfrost = BlockfrostClient(self.config.blockfrost_api_key)
            self.midnight = MidnightClient()

        if self.config.wallet_dir:
            self.thaw_data = load_thaw_data(self.config.wallet_dir)
            self.fee_wallet = FeeWallet(self.config.fee_wallet_dir)

    def display_header(self):
        """Display main header with status."""
        clear_screen()
        print("=" * 55)
        print(f"        Night Miner Token Redeemer v{VERSION}")
        print("=" * 55)

        if self.config.wallet_dir:
            wallet_name = os.path.basename(self.config.wallet_dir)
            print(f"\nWallet: {wallet_name}")

        if self.fee_wallet and self.fee_wallet.exists() and self.blockfrost:
            try:
                addr = self.fee_wallet.get_address()
                balance = self.blockfrost.get_address_balance(addr)
                print(f"Fee Wallet: {truncate_address(addr, 30)} ({format_ada(balance)})")
            except Exception as e:
                logger.error(f"Error getting fee wallet balance: {e}")
                print("Fee Wallet: Error loading")
        elif self.fee_wallet:
            print("Fee Wallet: Not created yet")

        # Show thaw summary
        if self.thaw_data.get("addresses"):
            summary = get_thaw_summary(self.thaw_data)
            print()
            if summary["total_redeemable"] > 0:
                print(f"Redeemable: {format_night_short(summary['total_redeemable'])} NIGHT ({summary['redeemable_count']} addresses)")
            else:
                print("Redeemable: None")

            if summary["total_upcoming"] > 0:
                next_date = min(summary["upcoming_by_date"].keys()) if summary["upcoming_by_date"] else "Unknown"
                print(f"Upcoming:   {format_night_short(summary['total_upcoming'])} NIGHT (next: {next_date})")

        print("\n" + "-" * 55)

    def main_menu(self):
        """Main menu loop."""
        while True:
            self.display_header()

            print("\n  [1] Refresh Schedules    - Fetch latest thaw data from API")
            print("  [2] View Schedules       - See redeemable & upcoming thaws")
            print("  [3] Redeem Tokens        - Claim your thawed NIGHT tokens")
            print("  [4] Consolidate          - Send all NIGHT to one wallet")
            print("  [5] Settings             - Configure wallet, API key, etc.")
            print("\n  [q] Quit")
            print("\n" + "-" * 55)

            choice = input("\nChoice: ").strip().lower()
            logger.debug(f"Menu choice: {choice}")

            if choice == '1':
                self.menu_refresh()
            elif choice == '2':
                self.menu_view_schedules()
            elif choice == '3':
                self.menu_redeem()
            elif choice == '4':
                self.menu_consolidate()
            elif choice == '5':
                self.menu_settings()
            elif choice == 'q':
                logger.info("User quit")
                print("\nGoodbye!")
                break
            else:
                print("\nInvalid choice.")
                time.sleep(1)

    def menu_refresh(self):
        """Refresh thaw schedules."""
        self.display_header()
        print("\n--- Refresh Thaw Schedules ---\n")
        print("This fetches the latest thaw schedule data from the Midnight API")
        print("for all your mining addresses. It shows which tokens are redeemable")
        print("now and which are still locked (with their unlock dates).")
        print()
        print("-" * 55)
        logger.info("Starting schedule refresh")

        if not self.config.wallet_dir:
            print("Wallet not configured. Use Settings first.")
            input("\nPress Enter to return...")
            return

        addresses = find_wallet_addresses(self.config.wallet_dir)
        if not addresses:
            print("No wallet addresses found.")
            input("\nPress Enter to return...")
            return

        print(f"Found {len(addresses)} wallet addresses.\n")

        # Determine what to refresh
        saved = self.thaw_data.get("addresses", {})
        if not saved:
            to_check = addresses
            print("No existing data. Refreshing all addresses...")
        else:
            to_check = []
            for wa in addresses:
                if wa.address not in saved:
                    to_check.append(wa)
                elif saved[wa.address].get("failed"):
                    to_check.append(wa)
                else:
                    thaws = saved[wa.address].get("thaws", [])
                    if any(t.get("status") == "redeemable" for t in thaws):
                        to_check.append(wa)

            if not to_check:
                print("All addresses up to date!")
                print("\n[f] Force refresh all")
                print("[Enter] Return to menu")
                choice = input("\nChoice: ").strip().lower()
                if choice == 'f':
                    to_check = addresses
                else:
                    return

            print(f"Refreshing {len(to_check)} addresses...")

        print("(Press Ctrl+C to stop)\n")

        midnight = MidnightClient()

        try:
            for i, wa in enumerate(to_check):
                print(f"[{i+1}/{len(to_check)}] {wa.skey_file.name}...", end=" ", flush=True)

                try:
                    schedule = midnight.get_thaw_schedule(wa.address)

                    if schedule:
                        thaws = schedule.get("thaws", [])
                        redeemable = sum(1 for t in thaws if t.get("status") == "redeemable")
                        upcoming = sum(1 for t in thaws if t.get("status") == "upcoming")
                        confirmed = sum(1 for t in thaws if t.get("status") == "confirmed")

                        parts = []
                        if redeemable:
                            parts.append(f"{redeemable} redeemable")
                        if upcoming:
                            parts.append(f"{upcoming} upcoming")
                        if confirmed:
                            parts.append(f"{confirmed} redeemed")
                        print(" | ".join(parts) if parts else "no thaws")

                        self.thaw_data["addresses"][wa.address] = {
                            "last_checked": datetime.now(timezone.utc).isoformat(),
                            "thaws": thaws,
                            "failed": False,
                            "key_index": wa.index,
                            "skey_file": wa.skey_file.name,
                        }
                    else:
                        print("no schedule")
                        self.thaw_data["addresses"][wa.address] = {
                            "last_checked": datetime.now(timezone.utc).isoformat(),
                            "thaws": [],
                            "failed": False,
                            "key_index": wa.index,
                            "skey_file": wa.skey_file.name,
                        }

                except Exception as e:
                    print(f"FAILED: {e}")
                    logger.error(f"Failed to check {wa.skey_file.name}: {e}")
                    self.thaw_data["addresses"][wa.address] = {
                        "last_checked": datetime.now(timezone.utc).isoformat(),
                        "failed": True,
                        "error": str(e),
                        "key_index": wa.index,
                        "skey_file": wa.skey_file.name,
                    }

                save_thaw_data(self.config.wallet_dir, self.thaw_data)

                if i < len(to_check) - 1:
                    time.sleep(API_CALL_DELAY)

        except KeyboardInterrupt:
            print("\n\nStopped. Progress saved.")
            logger.info("Refresh interrupted by user")

        self.thaw_data["last_full_refresh"] = datetime.now(timezone.utc).isoformat()
        save_thaw_data(self.config.wallet_dir, self.thaw_data)

        print("\nRefresh complete!")
        input("\nPress Enter to return...")

    def menu_view_schedules(self):
        """View thaw schedules in chronological order."""
        self.display_header()
        print("\n--- Thaw Schedules ---\n")
        print("Shows all your tokens organized by status:")
        print("  - Redeemable Now: Tokens you can claim immediately")
        print("  - Upcoming Thaws: Tokens still locked, grouped by unlock date")
        print()
        print("-" * 55)

        if not self.thaw_data.get("addresses"):
            print("No schedule data. Use [1] Refresh Schedules first.")
            input("\nPress Enter to return...")
            return

        # Collect all thaws
        redeemable_list = []
        upcoming_list = []
        confirmed_list = []

        for address, data in self.thaw_data.get("addresses", {}).items():
            if data.get("failed"):
                continue

            skey_file = data.get("skey_file", "unknown")
            key_index = data.get("key_index", 0)

            for thaw in data.get("thaws", []):
                amount = thaw.get("amount", 0)
                status = thaw.get("status", "")
                thaw_date = thaw.get("thawing_period_start", "")[:10] or "Unknown"
                tx_id = thaw.get("transaction_id")

                entry = {
                    "address": address,
                    "skey_file": skey_file,
                    "key_index": key_index,
                    "amount": amount,
                    "date": thaw_date,
                    "tx_id": tx_id,
                }

                if status == "redeemable":
                    redeemable_list.append(entry)
                elif status == "upcoming":
                    upcoming_list.append(entry)
                elif status == "confirmed":
                    confirmed_list.append(entry)

        # Sort upcoming by date
        upcoming_list.sort(key=lambda x: x["date"])

        # Display redeemable
        print("=" * 55)
        print("REDEEMABLE NOW")
        print("=" * 55)

        if redeemable_list:
            total_redeemable = 0
            for entry in redeemable_list:
                print(f"  {entry['skey_file']}: {format_night(entry['amount'])} NIGHT")
                total_redeemable += entry["amount"]
            print("-" * 55)
            print(f"  Total: {format_night(total_redeemable)} NIGHT ({len(redeemable_list)} addresses)")
        else:
            print("  None")
        print()

        # Display upcoming grouped by date
        print("=" * 55)
        print("UPCOMING THAWS (chronological)")
        print("=" * 55)

        if upcoming_list:
            # Group by date
            by_date = {}
            for entry in upcoming_list:
                date = entry["date"]
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(entry)

            total_upcoming = 0
            for date in sorted(by_date.keys()):
                entries = by_date[date]
                date_total = sum(e["amount"] for e in entries)
                total_upcoming += date_total
                print(f"\n  {date}:")
                print(f"    {format_night(date_total)} NIGHT ({len(entries)} addresses)")

            print()
            print("-" * 55)
            print(f"  Total upcoming: {format_night(total_upcoming)} NIGHT")
        else:
            print("  None")

        # Display confirmed (already redeemed)
        if confirmed_list:
            print()
            print("=" * 55)
            print("ALREADY REDEEMED")
            print("=" * 55)

            total_confirmed = 0
            for entry in confirmed_list:
                tx_short = entry["tx_id"][:16] + "..." if entry.get("tx_id") else "N/A"
                print(f"  {entry['skey_file']}: {format_night(entry['amount'])} NIGHT")
                print(f"    Date: {entry['date']} | TX: {tx_short}")
                total_confirmed += entry["amount"]
            print("-" * 55)
            print(f"  Total redeemed: {format_night(total_confirmed)} NIGHT")

        print()
        input("\nPress Enter to return...")

    def menu_redeem(self):
        """Redeem tokens."""
        self.display_header()
        print("\n--- Redeem NIGHT Tokens ---\n")
        print("Claims your thawed NIGHT tokens from all mining addresses.")
        print("This builds and submits redemption transactions for each address")
        print("that has redeemable tokens.")
        print()
        print("=" * 55)
        print("IMPORTANT: Wait for ALL tokens to thaw before redeeming!")
        print("=" * 55)
        print("Redemption costs ~3.25 ADA per address. If you redeem now and")
        print("redeem again later when more tokens thaw, you pay DOUBLE the fees.")
        print()
        print("Use [2] View Schedules to check if you have upcoming thaws.")
        print("When 'Upcoming Thaws' is empty, ALL your tokens are ready.")
        print()
        print("-" * 55)
        logger.info("Starting redemption flow")

        # Check prerequisites
        if not self.fee_wallet:
            print("Fee wallet not configured. Use Settings first.")
            input("\nPress Enter to return...")
            return

        if not self.fee_wallet.exists():
            print("Fee wallet not created yet.")
            print("\nWould you like to create one now? (y/n): ", end="")
            if input().strip().lower() == 'y':
                try:
                    addr = self.fee_wallet.generate()
                    print(f"\nCreated: {addr}")
                    print("\nSend ADA to this address before redeeming.")
                except Exception as e:
                    print(f"\nFailed to create: {e}")
                    logger.error(f"Fee wallet creation failed: {e}")
            input("\nPress Enter to return...")
            return

        balance = self.blockfrost.get_address_balance(self.fee_wallet.get_address())
        if balance < MIN_BALANCE_TO_START:
            print(f"Insufficient balance: {format_ada(balance)}")
            print(f"Need at least {format_ada(MIN_BALANCE_TO_START)} to start.")
            print(f"\nFee wallet address:")
            print(f"  {self.fee_wallet.get_address()}")
            input("\nPress Enter to return...")
            return

        # Get redeemable addresses
        redeemable = get_redeemable_addresses(self.thaw_data)
        if not redeemable:
            print("No redeemable tokens found.")
            print("\nUse [1] Refresh Schedules to check for new redeemable tokens.")
            input("\nPress Enter to return...")
            return

        redeemable.sort(key=lambda x: (x.get("key_index") is None, x.get("key_index") or 0))

        # Preview
        total = sum(r["amount"] for r in redeemable)
        print(f"Found {len(redeemable)} addresses with redeemable tokens:")
        print("-" * 55)
        for r in redeemable[:10]:
            print(f"  {r.get('skey_file', 'Unknown'):<22} {format_night(r['amount']):>18}")
        if len(redeemable) > 10:
            print(f"  ... and {len(redeemable) - 10} more")
        print("-" * 55)
        print(f"  {'TOTAL':<22} {format_night(total):>18}")
        print("-" * 55)

        print(f"\nFee Wallet: {format_ada(balance)}")
        est_cost = len(redeemable) * MIN_BALANCE_PER_REDEMPTION
        print(f"Est. Cost:  {format_ada(est_cost)}")

        if balance < est_cost:
            affordable = balance // MIN_BALANCE_PER_REDEMPTION
            print(f"\nNote: Can afford ~{affordable} of {len(redeemable)} redemptions")

        # Confirm
        print("\n" + "=" * 55)
        confirm = input("Proceed? (type 'yes' to confirm): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled.")
            input("\nPress Enter to return...")
            return

        # Execute
        logger.info(f"Starting batch redemption: {len(redeemable)} addresses")
        print("\nStarting redemption...")
        print("=" * 55)

        results = []

        try:
            for i, addr_info in enumerate(redeemable):
                address = addr_info["address"]
                skey_file = addr_info.get("skey_file", "Unknown")
                amount = addr_info.get("amount", 0)

                # Check balance
                balance = self.blockfrost.get_address_balance(self.fee_wallet.get_address())
                if balance < MIN_BALANCE_PER_REDEMPTION:
                    print(f"\n[STOPPING] Insufficient funds: {format_ada(balance)}")
                    print(f"           Completed {i} of {len(redeemable)}")
                    logger.warning(f"Batch stopped due to low balance: {balance}")

                    for remaining in redeemable[i:]:
                        results.append(BatchResult(
                            remaining["address"], False, "Skipped - insufficient funds",
                            skey_file=remaining.get("skey_file")
                        ))
                    break

                print(f"\n[{i+1}/{len(redeemable)}] {skey_file} ({format_night(amount)})")
                print(f"    Fee wallet: {format_ada(balance)}")

                result = redeem_single(
                    address, skey_file, self.config.wallet_dir,
                    self.fee_wallet, self.blockfrost, self.midnight
                )
                results.append(result)

                if result.success:
                    print(f"OK")
                    print(f"    TX: {result.tx_id[:24]}...")
                else:
                    print(f"FAILED: {result.message}")

                if i < len(redeemable) - 1 and result.success:
                    time.sleep(BATCH_DELAY)

        except KeyboardInterrupt:
            print("\n\nInterrupted.")
            logger.warning("Redemption interrupted by user")

        # Summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print("\n" + "=" * 55)
        print("Redemption Complete")
        print("=" * 55)
        print(f"Successful: {len(successful)}")
        print(f"Failed:     {len(failed)}")

        if successful:
            total = sum(r.amount or 0 for r in successful)
            print(f"Total:      {format_night(total)}")

        save_batch_results(results, "redemption")
        logger.info(f"Redemption complete: {len(successful)} successful, {len(failed)} failed")

        input("\nPress Enter to return...")

    def menu_consolidate(self):
        """Consolidate NIGHT to single address."""
        self.display_header()
        print("\n--- Consolidate NIGHT Tokens ---\n")
        print("Sends all your redeemed NIGHT tokens from your mining addresses")
        print("to a single destination wallet of your choice.")
        print()
        print("=" * 55)
        print("IMPORTANT: Redeem ALL tokens before consolidating!")
        print("=" * 55)
        print("Consolidation costs ~0.5 ADA per address. If you consolidate now")
        print("and consolidate again later after redeeming more tokens, you pay")
        print("DOUBLE the fees.")
        print()
        print("Best workflow: Wait for all thaws -> Redeem all -> Consolidate once")
        print()
        print("-" * 55)
        logger.info("Starting consolidation flow")

        # Check prerequisites
        if not self.fee_wallet or not self.fee_wallet.exists():
            print("Fee wallet not ready. Use Settings first.")
            input("\nPress Enter to return...")
            return

        balance = self.blockfrost.get_address_balance(self.fee_wallet.get_address())
        if balance < MIN_BALANCE_TO_START:
            print(f"Insufficient balance: {format_ada(balance)}")
            print(f"Need at least {format_ada(MIN_BALANCE_TO_START)} to start.")
            input("\nPress Enter to return...")
            return

        # Scan for NIGHT
        print("Scanning mining addresses for NIGHT tokens...")
        addresses = self.thaw_data.get("addresses", {})
        consolidatable = []

        for addr, data in addresses.items():
            if data.get("failed"):
                continue

            utxos = self.blockfrost.get_address_utxos_with_assets(addr)
            night = 0
            for utxo in utxos:
                for asset in utxo["assets"]:
                    if asset["policy_id"] == NIGHT_POLICY_ID:
                        night += asset["quantity"]

            if night > 0:
                consolidatable.append({
                    "address": addr,
                    "skey_file": data.get("skey_file", "Unknown"),
                    "night": night
                })
            time.sleep(0.3)

        if not consolidatable:
            print("\nNo addresses with NIGHT tokens found.")
            input("\nPress Enter to return...")
            return

        # Preview
        total_night = sum(c["night"] for c in consolidatable)
        print(f"\nFound {len(consolidatable)} addresses with NIGHT:")
        print("-" * 55)
        for c in consolidatable[:10]:
            print(f"  {c['skey_file']:<22} {format_night(c['night']):>18}")
        if len(consolidatable) > 10:
            print(f"  ... and {len(consolidatable) - 10} more")
        print("-" * 55)
        print(f"  {'TOTAL':<22} {format_night(total_night):>18}")
        print("-" * 55)

        # Get destination
        print("\nEnter destination address:")
        print("(The wallet where you want all NIGHT tokens sent)")
        destination = input("\nDestination: ").strip()

        if not destination.startswith("addr1"):
            print("\nInvalid address. Must start with 'addr1'")
            input("\nPress Enter to return...")
            return

        # Confirm
        print("\n" + "=" * 55)
        print(f"Destination: {truncate_address(destination, 45)}")
        print(f"Total NIGHT: {format_night(total_night)}")
        print("=" * 55)

        confirm = input("Proceed? (type 'yes' to confirm): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled.")
            input("\nPress Enter to return...")
            return

        # Execute
        logger.info(f"Starting consolidation: {len(consolidatable)} addresses -> {destination}")
        print("\nStarting consolidation...")
        print("=" * 55)

        results = []

        try:
            for i, addr_info in enumerate(consolidatable):
                address = addr_info["address"]
                skey_file = addr_info.get("skey_file", "Unknown")

                balance = self.blockfrost.get_address_balance(self.fee_wallet.get_address())
                if balance < MIN_BALANCE_PER_CONSOLIDATION:
                    print(f"\n[STOPPING] Insufficient funds: {format_ada(balance)}")
                    print(f"           Completed {i} of {len(consolidatable)}")

                    for remaining in consolidatable[i:]:
                        results.append(BatchResult(
                            remaining["address"], False, "Skipped - insufficient funds",
                            skey_file=remaining.get("skey_file")
                        ))
                    break

                print(f"\n[{i+1}/{len(consolidatable)}] {skey_file}")
                print(f"    Fee wallet: {format_ada(balance)}")

                skey_path = find_skey_path(skey_file, self.config.wallet_dir)
                if not skey_path:
                    print(f"    FAILED: Key not found")
                    results.append(BatchResult(address, False, "Key not found", skey_file=skey_file))
                    continue

                result = consolidate_single(
                    address, destination, skey_path,
                    self.fee_wallet, self.blockfrost
                )
                result.skey_file = skey_file
                results.append(result)

                if result.success:
                    print(f"OK")
                    print(f"    TX: {result.tx_id[:24]}...")
                else:
                    print(f"    FAILED: {result.message}")

                if i < len(consolidatable) - 1 and result.success:
                    time.sleep(BATCH_DELAY)

        except KeyboardInterrupt:
            print("\n\nInterrupted.")

        # Summary
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print("\n" + "=" * 55)
        print("Consolidation Complete")
        print("=" * 55)
        print(f"Successful: {len(successful)}")
        print(f"Failed:     {len(failed)}")

        if successful:
            total = sum(r.amount or 0 for r in successful)
            print(f"Total:      {format_night(total)}")

        save_batch_results(results, "consolidation", destination)

        # Offer to drain fee wallet
        print("\n" + "-" * 55)
        fee_balance = self.blockfrost.get_address_balance(self.fee_wallet.get_address())
        if fee_balance >= 1_200_000:  # Need at least 1.2 ADA to drain
            print(f"\nFee wallet has {format_ada(fee_balance)} remaining.")
            print("Would you like to send this to your destination wallet too?")
            print()
            print("  [y] Yes - Send remaining ADA to destination")
            print("  [n] No  - Keep ADA in fee wallet for future use")
            print()
            drain_choice = input("Choice [n]: ").strip().lower()

            if drain_choice == 'y':
                print(f"\nDraining fee wallet to {truncate_address(destination, 40)}...")
                print(f"    Balance: {format_ada(fee_balance)}")

                drain_result = drain_fee_wallet(destination, self.fee_wallet, self.blockfrost)

                if drain_result.success:
                    print(f"OK")
                    print(f"    TX: {drain_result.tx_id[:24]}...")
                    print(f"    Sent: {format_ada(drain_result.amount)}")
                    print(f"\nFee wallet emptied. All funds sent to destination.")
                else:
                    print(f"FAILED: {drain_result.message}")
        else:
            print(f"\nFee wallet balance: {format_ada(fee_balance)}")
            if fee_balance > 0:
                print("(Too low to transfer - keeping for future use)")

        input("\nPress Enter to return...")

    def menu_settings(self):
        """Settings menu."""
        while True:
            self.display_header()
            print("\n--- Settings ---\n")
            print("Configure your wallet locations, API key, and fee wallet.")
            print()
            print("-" * 55)

            print(f"\n  [1] Wallet Directory")
            print(f"      Current: {self.config.wallet_dir or 'Not set'}")
            print()
            print(f"  [2] Blockfrost API Key")
            print(f"      Current: {'Set' if self.config.blockfrost_api_key else 'Not set'}")
            print()
            print(f"  [3] Fee Wallet")
            if self.fee_wallet and self.fee_wallet.exists():
                print(f"      Address: {truncate_address(self.fee_wallet.get_address(), 40)}")
            else:
                print(f"      Status: Not created")
            print()
            print(f"  [4] View Log File")
            print()
            print(f"  [b] Back to main menu")
            print()

            choice = input("Choice: ").strip().lower()

            if choice == '1':
                self._settings_wallet_dir()
            elif choice == '2':
                self._settings_api_key()
            elif choice == '3':
                self._settings_fee_wallet()
            elif choice == '4':
                self._settings_view_log()
            elif choice == 'b':
                break
            else:
                print("\nInvalid choice.")
                time.sleep(1)

    def _settings_wallet_dir(self):
        """Change wallet directory."""
        print("\nCurrent: " + (self.config.wallet_dir or "Not set"))

        if TKINTER_AVAILABLE:
            print("\nPress Enter to open folder selector...")
            input()
            root = tk.Tk()
            root.withdraw()
            new_dir = filedialog.askdirectory(title="Select wallet folder")
        else:
            new_dir = input("\nNew path (or Enter to cancel): ").strip()

        if new_dir and os.path.isdir(new_dir):
            addresses = find_wallet_addresses(new_dir)
            if addresses:
                self.config.wallet_dir = new_dir
                self.config.save()
                self.thaw_data = load_thaw_data(new_dir)
                print(f"\nSet to: {new_dir}")
                print(f"Found {len(addresses)} addresses.")
            else:
                print("\nNo wallet files found in that directory.")
        elif new_dir:
            print("\nDirectory not found.")

        input("\nPress Enter to continue...")

    def _settings_api_key(self):
        """Change Blockfrost API key."""
        print("\nGet a free key at blockfrost.io\n")

        open_browser = input("Open Blockfrost website in browser? [Y/n]: ").strip().lower()
        if open_browser != 'n':
            print("\nOpening browser...")
            webbrowser.open("https://blockfrost.io/dashboard")
            print()

        new_key = input("New API key (or Enter to cancel): ").strip()

        if new_key:
            print("\nTesting connection...")
            test_client = BlockfrostClient(new_key)
            if test_client.test_connection():
                self.config.blockfrost_api_key = new_key
                self.config.save()
                self.blockfrost = test_client
                self.midnight = MidnightClient()
                print("API key saved!")
            else:
                print("Connection failed. Key not saved.")

        input("\nPress Enter to continue...")

    def _settings_fee_wallet(self):
        """Fee wallet settings."""
        if self.fee_wallet and self.fee_wallet.exists():
            addr = self.fee_wallet.get_address()
            print(f"\nFee Wallet Address:")
            print(f"  {addr}")
            balance = 0
            if self.blockfrost:
                balance = self.blockfrost.get_address_balance(addr)
                print(f"\nBalance: {format_ada(balance)}")
            print("\n(Send ADA to this address to fund operations)")

            # Offer to drain if balance is sufficient (need 1.2 ADA min)
            if balance >= 1_200_000:
                print("\n" + "-" * 55)
                print("\n  [d] Drain fee wallet (send all ADA to another address)")
                print("  [Enter] Return to settings")
                choice = input("\nChoice: ").strip().lower()

                if choice == 'd':
                    print("\nEnter destination address for remaining ADA:")
                    destination = input("\nDestination: ").strip()

                    if not destination.startswith("addr1"):
                        print("\nInvalid address. Must start with 'addr1'")
                    else:
                        print(f"\nSending {format_ada(balance)} to:")
                        print(f"  {truncate_address(destination, 45)}")
                        confirm = input("\nProceed? (y/n): ").strip().lower()

                        if confirm == 'y':
                            print(f"\nDraining fee wallet...")
                            result = drain_fee_wallet(destination, self.fee_wallet, self.blockfrost)

                            if result.success:
                                print(f"OK")
                                print(f"    TX: {result.tx_id[:24]}...")
                                print(f"    Sent: {format_ada(result.amount)}")
                                print(f"\nFee wallet emptied successfully.")
                                print("(Balance may take ~30 seconds to update in menu)")
                            else:
                                print(f"FAILED: {result.message}")
                        else:
                            print("\nCancelled.")
        else:
            print("\nNo fee wallet exists.")
            confirm = input("\nCreate one now? (y/n): ").strip().lower()
            if confirm == 'y':
                try:
                    if not self.fee_wallet:
                        self.fee_wallet = FeeWallet(self.config.fee_wallet_dir)
                    addr = self.fee_wallet.generate()
                    print(f"\nCreated!")
                    print(f"Address: {addr}")
                    print("\nSend ADA to this address before redeeming.")
                except Exception as e:
                    print(f"\nFailed: {e}")

        input("\nPress Enter to continue...")

    def _settings_view_log(self):
        """View recent log entries."""
        clear_screen()
        print("=" * 55)
        print("              Recent Log Entries")
        print("=" * 55)
        print(f"\nLog file: {LOG_FILE}")
        print("-" * 55)

        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                # Show last 30 lines
                for line in lines[-30:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"Error reading log: {e}")

        print("-" * 55)
        print("\nSend this file to the developer if you need help.")
        input("\nPress Enter to continue...")


# ==============================================================================
# Entry Point
# ==============================================================================

def main():
    """Main entry point."""
    if not PYCARDANO_AVAILABLE:
        print("\n" + "=" * 55)
        print("ERROR: Required library not installed")
        print("=" * 55)
        print("\nPlease run: pip install pycardano")
        print("\nOr use the setup script: ./setup.sh")
        sys.exit(1)

    try:
        app = NightManager()

        # Loop setup until complete
        while app.setup_required():
            app.run_setup()

        app.initialize()
        app.main_menu()

    except KeyboardInterrupt:
        logger.info("Application interrupted")
        print("\n\nGoodbye!")
    except Exception as e:
        logger.exception("Fatal error")
        print(f"\nFatal error: {e}")
        print(f"\nCheck {LOG_FILE} for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
