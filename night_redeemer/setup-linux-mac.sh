#!/bin/bash
# ==============================================================================
# Night Miner Token Redeemer - Setup Script (Linux/Mac)
#
# This script sets up everything you need to run the Night Miner Token Redeemer.
# Just run: ./setup-linux-mac.sh
# ==============================================================================

INSTALL_DIR="night-redeemer"
SETUP_SUCCESS=false

# Cleanup on failure, pause on exit
cleanup_and_pause() {
    if [ "$SETUP_SUCCESS" = false ]; then
        echo ""
        echo "--------------------------------------------------------"
        echo "Setup failed. Cleaning up..."
        echo "--------------------------------------------------------"
        rm -rf "$INSTALL_DIR" 2>/dev/null
        echo "Cleaned up. Fix the issue above and run setup again."
    fi
    echo ""
    read -p "Press Enter to close..."
}
trap cleanup_and_pause EXIT

echo "========================================================"
echo "     Night Miner Token Redeemer - Setup Script"
echo "========================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}!${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

info() {
    echo -e "${BLUE}i${NC} $1"
}

# ==============================================================================
# Step 1: Check Python
# ==============================================================================
echo "Step 1: Checking Python installation..."
echo "--------------------------------------------------------"

PYTHON_CMD=""

# Prefer SYSTEM Python to avoid issues with portable/standalone builds
if [ -x "/usr/bin/python3.12" ]; then
    PYTHON_CMD="/usr/bin/python3.12"
    success "Found system Python 3.12"
elif [ -x "/usr/bin/python3.11" ]; then
    PYTHON_CMD="/usr/bin/python3.11"
    success "Found system Python 3.11"
elif [ -x "/usr/bin/python3.10" ]; then
    PYTHON_CMD="/usr/bin/python3.10"
    success "Found system Python 3.10"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    success "Found Python 3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    success "Found Python 3.11"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)

    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 8 ] && [ "$PY_MINOR" -lt 14 ]; then
        PYTHON_CMD="python3"
        success "Found Python $PY_VERSION"
    else
        warning "Python $PY_VERSION found but may have compatibility issues"
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    error "Python 3.8-3.12 not found!"
    echo ""
    echo "Please install Python 3.12:"
    echo ""
    echo "  Fedora/RHEL:   sudo dnf install python3.12"
    echo "  Ubuntu/Debian: sudo apt install python3.12"
    echo "  macOS:         brew install python@3.12"
    echo ""
    exit 1
fi

# ==============================================================================
# Step 2: Check for night_redeemer.py
# ==============================================================================
echo ""
echo "Step 2: Checking for night_redeemer.py..."
echo "--------------------------------------------------------"

if [ ! -f "night_redeemer.py" ]; then
    error "night_redeemer.py not found!"
    echo "   Make sure night_redeemer.py is in the same folder as this script"
    exit 1
fi
success "Found night_redeemer.py"

# ==============================================================================
# Step 3: Create installation folder
# ==============================================================================
echo ""
echo "Step 3: Creating installation folder..."
echo "--------------------------------------------------------"

if [ -d "$INSTALL_DIR" ]; then
    warning "$INSTALL_DIR/ already exists"
    read -p "Delete and reinstall? [y/N]: " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf "$INSTALL_DIR"
        success "Removed old installation"
    else
        echo "Setup cancelled."
        SETUP_SUCCESS=true  # Don't clean up existing folder
        exit 0
    fi
fi

mkdir -p "$INSTALL_DIR"
success "Created $INSTALL_DIR/"

# Copy night_redeemer.py
cp night_redeemer.py "$INSTALL_DIR/"
success "Copied night_redeemer.py"

# Change to install directory
cd "$INSTALL_DIR"

# ==============================================================================
# Step 4: Create directory structure
# ==============================================================================
echo ""
echo "Step 4: Creating directory structure..."
echo "--------------------------------------------------------"

# Create mining-wallet folder with README
mkdir -p "mining-wallet"
cat > "mining-wallet/PUT_YOUR_KEYS_HERE.txt" << 'WALLET_README'
================================================================================
                        MINING WALLET FOLDER
              (Night Miner Token Redeemer)
================================================================================

This folder is where you put your mining wallet key files.

WHAT TO PUT HERE:
-----------------
Copy your mining wallet files into this folder. You need:

  - addr-0.addr    (address file)
  - addr-0.skey    (signing key - KEEP SECRET!)
  - addr-1.addr
  - addr-1.skey
  - ... and so on for each mining address

These files were created when you set up Midnight mining.


WHERE TO FIND THEM:
-------------------
Your mining wallet files are usually in a folder called:
  - auto-mine-wallet/
  - wallet/
  - Or wherever you saved them during mining setup


IMPORTANT - KEEP YOUR .skey FILES SAFE!
---------------------------------------
The .skey files are your private keys. Anyone with these files can
spend your tokens. Never share them or upload them anywhere.

================================================================================
WALLET_README
success "Created mining-wallet/"

# Create fee-wallet folder with README
mkdir -p "fee-wallet"
cat > "fee-wallet/ABOUT_FEE_WALLET.txt" << 'FEE_README'
================================================================================
                           FEE WALLET FOLDER
              (Night Miner Token Redeemer)
================================================================================

This folder will contain your "fee wallet" - a separate wallet used to pay
transaction fees when redeeming and consolidating your NIGHT tokens.

WHY A SEPARATE WALLET?
----------------------
Your mining addresses don't have any ADA in them - they only receive NIGHT
tokens. But Cardano transactions require ADA for fees. The fee wallet holds
the ADA needed to pay these fees.


WHAT WILL BE HERE:
------------------
After you create a fee wallet (in the tool's Settings), you'll see:

  - fee-wallet.addr    Your fee wallet's address
  - fee-wallet.skey    Private signing key (KEEP SECRET!)
  - fee-wallet.vkey    Public verification key


HOW TO USE:
-----------
1. Run the Night Miner Token Redeemer
2. Go to Settings -> Fee Wallet
3. Create the wallet (or it's created automatically when needed)
4. Send ADA to the address shown (5-10 ADA recommended to start)
5. Now you can redeem tokens!


COSTS:
------
  - Redeeming tokens:   ~3.5 ADA per address (most travels with tokens)
  - Consolidating:      ~0.5 ADA per address

Note: Most of the redemption ADA stays with your NIGHT tokens - you keep it!
See README.md for full cost breakdown.


KEEP THIS FOLDER SAFE!
----------------------
The .skey file is your private key. Back it up securely and never share it.

================================================================================
FEE_README
success "Created fee-wallet/"

# Create logs folder with README
mkdir -p "logs"
cat > "logs/ABOUT_LOGS.txt" << 'LOGS_README'
================================================================================
                              LOGS FOLDER
              (Night Miner Token Redeemer)
================================================================================

This folder contains log files from the Night Miner Token Redeemer.

WHAT'S HERE:
------------
  - night_redeemer.log    Detailed activity log

The log file records:
  - Every action you take in the tool
  - API requests and responses
  - Any errors that occur
  - Transaction details


WHEN TO USE:
------------
If something goes wrong, check this log file for details. You can share it
when asking for help - it doesn't contain your private keys.


SAFE TO DELETE:
---------------
You can delete old log files if they get too large. A new one will be
created automatically.

================================================================================
LOGS_README
success "Created logs/"

# ==============================================================================
# Step 5: Create virtual environment
# ==============================================================================
echo ""
echo "Step 5: Setting up Python environment..."
echo "--------------------------------------------------------"

# Try normal venv creation first
if $PYTHON_CMD -m venv venv 2>/dev/null; then
    success "Created virtual environment"
else
    # If that fails, try without pip (common on Fedora)
    warning "Standard venv failed, trying without pip..."
    if $PYTHON_CMD -m venv --without-pip venv 2>/dev/null; then
        success "Created virtual environment (without pip)"
    else
        error "Failed to create virtual environment"
        echo ""
        echo "Please install python3-venv and try again:"
        echo ""
        echo "  Ubuntu/Debian: sudo apt install python3-venv"
        echo "  Fedora:        sudo dnf install python3-libs"
        echo ""
        exit 1
    fi
fi

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    success "Activated virtual environment"

    # Add README to venv folder
    cat > "venv/DO_NOT_MODIFY.txt" << 'VENV_README'
================================================================================
                     PYTHON VIRTUAL ENVIRONMENT
              (Night Miner Token Redeemer)
================================================================================

This folder contains the Python virtual environment for the tool.

WHAT IS THIS?
-------------
A virtual environment is an isolated Python installation that keeps this
tool's dependencies separate from your system Python. This prevents
conflicts with other software on your computer.


DO NOT MODIFY:
--------------
  - Do not delete, rename, or move files in this folder
  - Do not manually install or remove packages here
  - Do not edit any files in this folder

If something breaks, delete the entire 'venv' folder and run setup again.


FOR ADVANCED USERS:
-------------------
To manually activate this environment:

  Linux/Mac:  source venv/bin/activate
  Windows:    venv\Scripts\activate.bat

To deactivate: type 'deactivate'

================================================================================
VENV_README
else
    error "Virtual environment activation script not found"
    exit 1
fi

# Check if pip exists IN THE VENV, if not bootstrap it
if [ ! -f "venv/bin/pip" ] && [ ! -f "venv/bin/pip3" ]; then
    info "Installing pip into virtual environment..."
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python /tmp/get-pip.py --quiet
    rm -f /tmp/get-pip.py
    if [ -f "venv/bin/pip" ]; then
        success "Installed pip"
    else
        error "Failed to install pip"
        echo ""
        echo "Try installing pip manually:"
        echo "  cd $INSTALL_DIR"
        echo "  source venv/bin/activate"
        echo "  curl https://bootstrap.pypa.io/get-pip.py | python"
        echo ""
        exit 1
    fi
fi

# ==============================================================================
# Step 6: Install dependencies
# ==============================================================================
echo ""
echo "Step 6: Installing dependencies..."
echo "--------------------------------------------------------"

python -m pip install --upgrade pip --quiet 2>/dev/null
success "Updated pip"

info "Installing pycardano and requests (this may take a moment)..."
INSTALL_OUTPUT=$(python -m pip install pycardano requests 2>&1)
if [ $? -eq 0 ]; then
    success "Installed pycardano and requests"
else
    error "Failed to install dependencies"
    echo ""
    echo "Error details:"
    echo "$INSTALL_OUTPUT" | tail -20
    echo ""
    echo "--------------------------------------------------------"
    echo ""
    echo "This may be caused by missing build tools. Try:"
    echo ""
    echo "  Fedora:        sudo dnf install gcc python3-devel"
    echo "  Ubuntu/Debian: sudo apt install gcc python3-dev"
    echo ""
    exit 1
fi

# ==============================================================================
# Step 7: Verify installation
# ==============================================================================
echo ""
echo "Step 7: Verifying installation..."
echo "--------------------------------------------------------"

python -c "from pycardano import PaymentSigningKey; print('pycardano OK')" 2>/dev/null && success "pycardano works" || error "pycardano failed"
python -c "import requests; print('requests OK')" 2>/dev/null && success "requests works" || error "requests failed"

# ==============================================================================
# Step 8: Create run script
# ==============================================================================
echo ""
echo "Step 8: Creating run script..."
echo "--------------------------------------------------------"

cat > run.sh << 'EOF'
#!/bin/bash
# Night Miner Token Redeemer - Run Script
cd "$(dirname "$0")"
source venv/bin/activate
python night_redeemer.py
EOF
chmod +x run.sh
success "Created run.sh"

# ==============================================================================
# Done!
# ==============================================================================
SETUP_SUCCESS=true
echo ""
echo "========================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================================"
echo ""
echo "Installation created in: $INSTALL_DIR/"
echo ""
echo "  $INSTALL_DIR/"
echo "  ├── run.sh              <- Run this to start"
echo "  ├── night_redeemer.py"
echo "  ├── mining-wallet/      <- Put your wallet keys here"
echo "  ├── fee-wallet/"
echo "  ├── logs/"
echo "  └── venv/"
echo ""
echo "--------------------------------------------------------"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo ""
echo "  1. Go to the $INSTALL_DIR folder:"
echo -e "     ${GREEN}cd $INSTALL_DIR${NC}"
echo ""
echo "  2. Copy your mining wallet files to mining-wallet/"
echo ""
echo "  3. Run the tool:"
echo -e "     ${GREEN}./run.sh${NC}"
echo ""
echo "--------------------------------------------------------"
echo ""
