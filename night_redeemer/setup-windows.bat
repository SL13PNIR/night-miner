@echo off
REM ==============================================================================
REM Night Miner Token Redeemer - Setup Script (Windows)
REM
REM Just double-click this file to run setup.
REM ==============================================================================

set INSTALL_DIR=night-redeemer
set SETUP_SUCCESS=0

echo.
echo ========================================================
echo      Night Miner Token Redeemer - Setup Script
echo ========================================================
echo.

REM ==============================================================================
REM Step 1: Check Python
REM ==============================================================================
echo Step 1: Checking Python installation...
echo --------------------------------------------------------

set PYTHON_CMD=

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python --version 2>&1 | findstr /R "3\.[0-9]*\.[0-9]*" >nul
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python
        echo [OK] Found Python
        goto :python_found
    )
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python3
    echo [OK] Found Python3
    goto :python_found
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3
    echo [OK] Found Python (py launcher)
    goto :python_found
)

echo [ERROR] Python not found!
echo.
echo Please install Python first:
echo   1. Go to https://www.python.org/downloads/
echo   2. Download Python 3.12
echo   3. Run the installer
echo   4. IMPORTANT: Check "Add Python to PATH" during installation
echo   5. Restart your computer
echo   6. Run this setup again
echo.
pause
exit /b 1

:python_found

REM ==============================================================================
REM Step 2: Check for night_redeemer.py
REM ==============================================================================
echo.
echo Step 2: Checking for night_redeemer.py...
echo --------------------------------------------------------

if not exist "night_redeemer.py" (
    echo [ERROR] night_redeemer.py not found!
    echo         Make sure night_redeemer.py is in the same folder as this script
    goto :cleanup_fail
)
echo [OK] Found night_redeemer.py

REM ==============================================================================
REM Step 3: Create installation folder
REM ==============================================================================
echo.
echo Step 3: Creating installation folder...
echo --------------------------------------------------------

if exist "%INSTALL_DIR%" (
    echo [!] %INSTALL_DIR%\ already exists
    set /p confirm="Delete and reinstall? [y/N]: "
    if /i "%confirm%"=="y" (
        rmdir /s /q "%INSTALL_DIR%"
        echo [OK] Removed old installation
    ) else (
        echo Setup cancelled.
        set SETUP_SUCCESS=1
        pause
        exit /b 0
    )
)

mkdir "%INSTALL_DIR%"
echo [OK] Created %INSTALL_DIR%\

copy "night_redeemer.py" "%INSTALL_DIR%\" >nul
echo [OK] Copied night_redeemer.py

cd "%INSTALL_DIR%"

REM ==============================================================================
REM Step 4: Create directory structure
REM ==============================================================================
echo.
echo Step 4: Creating directory structure...
echo --------------------------------------------------------

mkdir "mining-wallet"
(
    echo ================================================================================
    echo                         MINING WALLET FOLDER
    echo               ^(Night Miner Token Redeemer^)
    echo ================================================================================
    echo.
    echo This folder is where you put your mining wallet key files.
    echo.
    echo WHAT TO PUT HERE:
    echo -----------------
    echo Copy your mining wallet files into this folder. You need:
    echo.
    echo   - addr-0.addr    ^(address file^)
    echo   - addr-0.skey    ^(signing key - KEEP SECRET!^)
    echo   - addr-1.addr
    echo   - addr-1.skey
    echo   - ... and so on for each mining address
    echo.
    echo These files were created when you set up Midnight mining.
    echo.
    echo.
    echo WHERE TO FIND THEM:
    echo -------------------
    echo Your mining wallet files are usually in a folder called:
    echo   - auto-mine-wallet\
    echo   - wallet\
    echo   - Or wherever you saved them during mining setup
    echo.
    echo.
    echo IMPORTANT - KEEP YOUR .skey FILES SAFE!
    echo ---------------------------------------
    echo The .skey files are your private keys. Anyone with these files can
    echo spend your tokens. Never share them or upload them anywhere.
    echo.
    echo ================================================================================
) > "mining-wallet\PUT_YOUR_KEYS_HERE.txt"
echo [OK] Created mining-wallet\

mkdir "fee-wallet"
(
    echo ================================================================================
    echo                            FEE WALLET FOLDER
    echo               ^(Night Miner Token Redeemer^)
    echo ================================================================================
    echo.
    echo This folder will contain your "fee wallet" - a separate wallet used to pay
    echo transaction fees when redeeming and consolidating your NIGHT tokens.
    echo.
    echo WHY A SEPARATE WALLET?
    echo ----------------------
    echo Your mining addresses don't have any ADA in them - they only receive NIGHT
    echo tokens. But Cardano transactions require ADA for fees. The fee wallet holds
    echo the ADA needed to pay these fees.
    echo.
    echo.
    echo WHAT WILL BE HERE:
    echo ------------------
    echo After you create a fee wallet ^(in the tool's Settings^), you'll see:
    echo.
    echo   - fee-wallet.addr    Your fee wallet's address
    echo   - fee-wallet.skey    Private signing key ^(KEEP SECRET!^)
    echo   - fee-wallet.vkey    Public verification key
    echo.
    echo.
    echo HOW TO USE:
    echo -----------
    echo 1. Run the Night Miner Token Redeemer
    echo 2. Go to Settings -^> Fee Wallet
    echo 3. Create the wallet ^(or it's created automatically when needed^)
    echo 4. Send ADA to the address shown ^(5-10 ADA recommended to start^)
    echo 5. Now you can redeem tokens!
    echo.
    echo.
    echo COSTS:
    echo ------
    echo   - Redeeming tokens:   ~3.5 ADA per address ^(most travels with tokens^)
    echo   - Consolidating:      ~0.5 ADA per address
    echo.
    echo Note: Most of the redemption ADA stays with your NIGHT tokens - you keep it!
    echo See README.md for full cost breakdown.
    echo.
    echo.
    echo KEEP THIS FOLDER SAFE!
    echo ----------------------
    echo The .skey file is your private key. Back it up securely and never share it.
    echo.
    echo ================================================================================
) > "fee-wallet\ABOUT_FEE_WALLET.txt"
echo [OK] Created fee-wallet\

mkdir "logs"
(
    echo ================================================================================
    echo                               LOGS FOLDER
    echo               ^(Night Miner Token Redeemer^)
    echo ================================================================================
    echo.
    echo This folder contains log files from the Night Miner Token Redeemer.
    echo.
    echo WHAT'S HERE:
    echo ------------
    echo   - night_redeemer.log    Detailed activity log
    echo.
    echo The log file records:
    echo   - Every action you take in the tool
    echo   - API requests and responses
    echo   - Any errors that occur
    echo   - Transaction details
    echo.
    echo.
    echo WHEN TO USE:
    echo ------------
    echo If something goes wrong, check this log file for details. You can share it
    echo when asking for help - it doesn't contain your private keys.
    echo.
    echo.
    echo SAFE TO DELETE:
    echo ---------------
    echo You can delete old log files if they get too large. A new one will be
    echo created automatically.
    echo.
    echo ================================================================================
) > "logs\ABOUT_LOGS.txt"
echo [OK] Created logs\

REM ==============================================================================
REM Step 5: Create virtual environment
REM ==============================================================================
echo.
echo Step 5: Setting up Python environment...
echo --------------------------------------------------------

%PYTHON_CMD% -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create virtual environment
    goto :cleanup_fail
)
echo [OK] Created virtual environment

(
    echo ================================================================================
    echo                      PYTHON VIRTUAL ENVIRONMENT
    echo               ^(Night Miner Token Redeemer^)
    echo ================================================================================
    echo.
    echo This folder contains the Python virtual environment for the tool.
    echo.
    echo WHAT IS THIS?
    echo -------------
    echo A virtual environment is an isolated Python installation that keeps this
    echo tool's dependencies separate from your system Python. This prevents
    echo conflicts with other software on your computer.
    echo.
    echo.
    echo DO NOT MODIFY:
    echo --------------
    echo   - Do not delete, rename, or move files in this folder
    echo   - Do not manually install or remove packages here
    echo   - Do not edit any files in this folder
    echo.
    echo If something breaks, delete the entire 'venv' folder and run setup again.
    echo.
    echo.
    echo FOR ADVANCED USERS:
    echo -------------------
    echo To manually activate this environment:
    echo.
    echo   Linux/Mac:  source venv/bin/activate
    echo   Windows:    venv\Scripts\activate.bat
    echo.
    echo To deactivate: type 'deactivate'
    echo.
    echo ================================================================================
) > "venv\DO_NOT_MODIFY.txt"

REM ==============================================================================
REM Step 6: Install dependencies
REM ==============================================================================
echo.
echo Step 6: Installing dependencies...
echo --------------------------------------------------------

call venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet 2>nul
echo [OK] Updated pip

echo [i] Installing pycardano and requests (this may take a moment)...
python -m pip install pycardano requests --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies
    goto :cleanup_fail
)
echo [OK] Installed pycardano and requests

REM ==============================================================================
REM Step 7: Verify installation
REM ==============================================================================
echo.
echo Step 7: Verifying installation...
echo --------------------------------------------------------

python -c "from pycardano import PaymentSigningKey" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] pycardano works
) else (
    echo [ERROR] pycardano failed to load
)

python -c "import requests" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] requests works
) else (
    echo [ERROR] requests failed to load
)

REM ==============================================================================
REM Step 8: Create run script
REM ==============================================================================
echo.
echo Step 8: Creating run script...
echo --------------------------------------------------------

(
    echo @echo off
    echo REM Night Miner Token Redeemer - Run Script
    echo cd /d "%%~dp0"
    echo call venv\Scripts\activate.bat
    echo python night_redeemer.py
    echo pause
) > "run.bat"
echo [OK] Created run.bat

REM ==============================================================================
REM Done!
REM ==============================================================================
set SETUP_SUCCESS=1
echo.
echo ========================================================
echo                    Setup Complete!
echo ========================================================
echo.
echo Installation created in: %INSTALL_DIR%\
echo.
echo   %INSTALL_DIR%\
echo   +-- run.bat             ^<- Double-click to start
echo   +-- night_redeemer.py
echo   +-- mining-wallet\      ^<- Put your wallet keys here
echo   +-- fee-wallet\
echo   +-- logs\
echo   +-- venv\
echo.
echo --------------------------------------------------------
echo.
echo NEXT STEPS:
echo.
echo   1. Open the %INSTALL_DIR% folder
echo.
echo   2. Copy your mining wallet files to mining-wallet\
echo.
echo   3. Double-click run.bat to start the tool
echo.
echo ========================================================
echo.
pause
goto :eof

:cleanup_fail
echo.
echo --------------------------------------------------------
echo Setup failed. Cleaning up...
echo --------------------------------------------------------
cd ..
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" 2>nul
echo Cleaned up. Fix the issue above and run setup again.
echo.
pause
