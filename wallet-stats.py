# ==============================================================================
# NIGHT Miner Wallet Statistics Tracker
#
# How to use this script:
# 1. Save this file as "wallet_stats.py" or another name you prefer.
# 2. Make sure you have a folder with a file named "wallet.json" inside it.
#    This script will read the addresses directly from that file.
# 3. Run this script from your terminal. It will guide you from there.
#
# The first time you run it, if it can't find the default "auto-mine-wallet"
# folder, it will automatically ask you to choose the correct folder.
# ==============================================================================

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta, timezone

# The tkinter library is used for the folder selection pop-up window.
import tkinter as tk
from tkinter import filedialog

# --- Script Settings ---

# The file where we save all the stats. This is created inside your wallet folder.
DATA_FILE_NAME = "address_stats.json"

# The default folder name we look for.
DEFAULT_WALLET_DIR = "auto-mine-wallet"

# The web address of the API that provides the statistics.
API_URL = "https://sm.midnight.gd/api/statistics/"

# A short pause (in seconds) between checking each address to be polite to the server.
API_CALL_DELAY = 3

# We'll show a friendly warning if you try to refresh all stats within this many hours.
REFRESH_COOLDOWN_HOURS = 6

# The conversion rate from the smallest unit (STAR) to the main token (NIGHT).
STAR_PER_NIGHT = 1_000_000


# --- Core Functions ---

def clear_terminal_screen():
    """Wipes the terminal screen clean for a fresh display."""
    os.system('cls' if os.name == 'nt' else 'clear')

def select_wallet_directory_popup():
    """
    Opens the pop-up window that lets the user choose a folder.
    Returns the path to the folder they chose.
    """
    print("\nPlease use the pop-up window to select your wallet folder...")
    # This part sets up and hides the main window for the pop-up.
    root = tk.Tk()
    root.withdraw()
    
    selected_path = filedialog.askdirectory(title="Select the folder containing your wallet.json file")
    
    if selected_path:
        print(f"\nFolder selected: {selected_path}")
    else:
        print("\nFolder selection was canceled.")
        
    return selected_path

def load_saved_stats(wallet_dir):
    """
    Loads the previously saved statistics from our data file.
    If the file doesn't exist, it returns a fresh, empty structure.
    """
    stats_file_path = os.path.join(wallet_dir, DATA_FILE_NAME)
    
    # This is the starting structure for our data if no file exists yet.
    empty_data = {"last_full_refresh": None, "addresses": {}}

    if not os.path.exists(stats_file_path):
        return empty_data

    try:
        with open(stats_file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If the file is corrupted or can't be read, we start fresh.
        print(f"\n[WARNING] Could not read '{stats_file_path}'. Starting with fresh data.")
        return empty_data

def save_stats_to_file(wallet_dir, stats_data):
    """Saves the current statistics to our data file in a readable format."""
    stats_file_path = os.path.join(wallet_dir, DATA_FILE_NAME)
    try:
        with open(stats_file_path, 'w') as f:
            json.dump(stats_data, f, indent=4)
    except IOError:
        print(f"\n[ERROR] Could not save data to '{stats_file_path}'!")


# --- Display Functions ---

def show_main_menu(wallet_dir, stats_data):
    """Displays the main menu of options to the user."""
    clear_terminal_screen()
    print("==================================================")
    print("       Night Miner Wallet Statistics Tracker")
    print("==================================================")
    print(f"Using Wallet Folder: {wallet_dir}")

    # Show the user when they last did a full refresh.
    last_refresh_time = stats_data.get("last_full_refresh")
    if last_refresh_time:
        # Convert the saved time into a more human-readable format.
        readable_time = datetime.fromisoformat(last_refresh_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Last Full Refresh:     {readable_time} (UTC)")
    else:
        print("Last Full Refresh:     Never")
        print("\nHint: Choose option [1] to get started.")

    print("\nCommands:")
    print("  [1] Check All Stats")
    print("  [2] Check New & Failed Addresses")
    print("  [3] Display Totals")
    print("  [4] Display Stats for Each Address")
    print("  [d] Change Wallet Directory")
    print("  [q] Quit")
    print("--------------------------------------------------")
    print("\n💡 TIP: STAR rates update daily (UTC). Today's solutions may show")
    print("    reduced NIGHT earnings until tomorrow's rate update.")
    print("--------------------------------------------------")

def show_total_stats(stats_data):
    """Calculates and displays the grand totals, showing both STAR and NIGHT."""
    clear_terminal_screen()
    print("==================================================")
    print("                 Overall Totals")
    print("==================================================")
    
    address_stats = stats_data.get("addresses", {})
    if not address_stats:
        print("\nNo stats have been collected yet.")
        print("Please run a refresh from the main menu first.")
    else:
        total_receipts = 0
        total_earnings_star = 0
        successful_addresses = 0

        for stats in address_stats.values():
            # We only add up the numbers if the last check was successful.
            if not stats.get('failed'):
                total_receipts += stats.get('crypto_receipts', 0)
                total_earnings_star += stats.get('night_earnings', 0)
                successful_addresses += 1

        # Convert total STAR to NIGHT tokens.
        total_earnings_night = total_earnings_star / STAR_PER_NIGHT

        print(f"\nStats from {successful_addresses} successfully checked addresses:")
        print("--------------------------------------------------")
        print(f"  Total Crypto Receipts:      {total_receipts}")
        print(f"  Total Night Earnings (STAR):  {total_earnings_star:,}")
        print(f"  Total Night Tokens (NIGHT): {total_earnings_night:.6f}")
        print("--------------------------------------------------")
        print("\n⚠️  NOTE: The server updates WORK to STAR conversion rates daily (UTC).")
        print("    Solutions found today may show lower NIGHT earnings until the next")
        print("    day when rates are updated. Check back tomorrow for accurate totals.")

    input("\nPress Enter to return to the menu...")

def show_individual_stats(stats_data):
    """Displays stats for each address, showing both STAR and NIGHT."""
    clear_terminal_screen()
    print("==================================================")
    print("             Individual Address Stats")
    print("==================================================")

    address_stats = stats_data.get("addresses", {})
    if not address_stats:
        print("\nNo stats have been collected yet.")
        print("Please run a refresh from the main menu first.")
    else:
        # Sort the addresses so they appear in the same order every time.
        for address, stats in sorted(address_stats.items()):
            print(f"\n--- Address: {address} ---")
            
            if stats.get('failed'):
                error_message = stats.get('error_info', 'Unknown error')
                print(f"  Status: FAILED")
                print(f"  Reason: {error_message}")
            else:
                earnings_star = stats.get('night_earnings', 0)
                # Convert this address's STAR earnings to NIGHT tokens.
                earnings_night = earnings_star / STAR_PER_NIGHT

                print("  Status:                   Success")
                print(f"  Crypto Receipts:          {stats.get('crypto_receipts', 'N/A')}")
                print(f"  Night Earnings (STAR):    {earnings_star:,}")
                print(f"  Night Tokens (NIGHT):   {earnings_night:.6f}")

            # Also show when this specific address was last checked.
            last_checked_time = stats.get('last_checked', 'Never')
            if last_checked_time != 'Never':
                readable_time = datetime.fromisoformat(last_checked_time).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  Last Checked:             {readable_time} (UTC)")

    input("\nPress Enter to return to the menu...")


# --- The Main Logic for Fetching Data ---

def get_stats_from_api(wallet_dir, stats_data, check_new_and_failed):
    """
    Connects to the API to get the latest stats for the addresses.
    This is the main workhorse function of the script.
    """
    wallet_file_path = os.path.join(wallet_dir, "wallet.json")
    
    try:
        with open(wallet_file_path, 'r') as f:
            wallet_json_data = json.load(f)
            addresses = [item["address"] for item in wallet_json_data["addresses"]]
    except FileNotFoundError:
        print(f"\n[ERROR] The 'wallet.json' file was not found in '{wallet_dir}'.")
        input("Press Enter to continue...")
        return stats_data
    except json.JSONDecodeError:
        print(f"\n[ERROR] Could not read 'wallet.json'. It seems to be formatted incorrectly.")
        input("Press Enter to continue...")
        return stats_data
    except (KeyError, TypeError):
        print(f"\n[ERROR] The 'wallet.json' file has an unexpected format.")
        print("         It should contain a key named 'addresses' with a list of wallets.")
        input("Press Enter to continue...")
        return stats_data

    if not addresses:
        print("\n[WARNING] No addresses were found inside your 'wallet.json' file.")
        input("Press Enter to continue...")
        return stats_data
        
    # Decide which addresses to check this run.
    if check_new_and_failed:
        # Create a list of addresses that are either new (not in our saved data)
        # or that failed on their last check.
        saved_address_stats = stats_data["addresses"]
        addresses_to_check = [
            addr for addr in addresses if 
            addr not in saved_address_stats or saved_address_stats[addr].get('failed')
        ]
        
        if not addresses_to_check:
            print("\nNo new or previously failed addresses to check. All up to date!")
            time.sleep(2)
            return stats_data
    else:
        # Otherwise, for a full refresh, we check every address in the file.
        addresses_to_check = addresses

    print(f"\nStarting to check {len(addresses_to_check)} addresses...")
    print("(You can press Ctrl+C at any time to stop. Progress is saved after each address.)\n")
    
    was_interrupted = False
    try:
        for index, address in enumerate(addresses_to_check):
            print(f"[{index + 1}/{len(addresses_to_check)}] Checking: {address}")
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            try:
                response = requests.get(f"{API_URL}{address}", headers=headers, timeout=15)
                response.raise_for_status()
                api_data = response.json()

                if api_data.get('local'):
                    receipts = api_data['local'].get('crypto_receipts', 0)
                    earnings = api_data['local'].get('night_allocation', 0)
                    print(f"  [SUCCESS] -> Receipts: {receipts}, Earnings: {earnings} STAR")
                    
                    stats_data["addresses"][address] = {
                        'last_checked': datetime.utcnow().isoformat(),
                        'crypto_receipts': receipts,
                        'night_earnings': earnings,
                        'failed': False
                    }
                else:
                    raise ValueError("'local' data not found in API response.")

            except Exception as e:
                print(f"  [FAILED] -> Error: {e}")
                stats_data["addresses"][address] = {
                    'last_checked': datetime.utcnow().isoformat(),
                    'failed': True,
                    'error_info': str(e)
                }
            
            save_stats_to_file(wallet_dir, stats_data)
            
            if index < len(addresses_to_check) - 1:
                time.sleep(API_CALL_DELAY)

    except KeyboardInterrupt:
        print("\n\nProcess stopped by user. Your progress has been saved.")
        was_interrupted = True

    # If this was a full refresh (not a partial one) and it finished without
    # being interrupted, we record the time.
    if not check_new_and_failed and not was_interrupted:
        stats_data["last_full_refresh"] = datetime.utcnow().isoformat()
        save_stats_to_file(wallet_dir, stats_data)
        print("\nFull refresh completed and timestamp recorded.")

    input("\nPress Enter to return to the menu...")
    return stats_data


# --- Program Start ---

def main():
    """The main function that runs the program loop."""
    wallet_dir = DEFAULT_WALLET_DIR

    if not os.path.isdir(wallet_dir):
        clear_terminal_screen()
        print("==================================================")
        print("           Welcome to the Stats Tracker")
        print("==================================================")
        print(f"\nThe default wallet folder ('{wallet_dir}') was not found.")
        input("\nPress Enter and I'll open a window for you to select the correct folder.")
        
        chosen_dir = select_wallet_directory_popup()
        
        if chosen_dir:
            wallet_dir = chosen_dir
        else:
            print("\nNo wallet folder was selected. The program will now exit.")
            sys.exit()

    stats_data = load_saved_stats(wallet_dir)

    while True:
        show_main_menu(wallet_dir, stats_data)
        choice = input("Enter your choice: ").lower().strip()

        if choice == '1':
            last_refresh = stats_data.get("last_full_refresh")
            should_proceed = True
            if last_refresh:
                time_since_refresh = datetime.now(timezone.utc) - datetime.fromisoformat(last_refresh).replace(tzinfo=timezone.utc)
                if time_since_refresh < timedelta(hours=REFRESH_COOLDOWN_HOURS):
                    print(f"\n[WARNING] You just did a refresh less than {REFRESH_COOLDOWN_HOURS} hours ago.")
                    confirm = input("To reduce server load, it's best to wait. Refresh anyway? (y/n): ").lower()
                    if confirm != 'y':
                        should_proceed = False
            
            if should_proceed:
                stats_data = get_stats_from_api(wallet_dir, stats_data, check_new_and_failed=False)

        elif choice == '2':
            stats_data = get_stats_from_api(wallet_dir, stats_data, check_new_and_failed=True)

        elif choice == '3':
            show_total_stats(stats_data)

        elif choice == '4':
            show_individual_stats(stats_data)

        elif choice == 'd':
            new_dir = select_wallet_directory_popup()
            if new_dir:
                wallet_dir = new_dir
                stats_data = load_saved_stats(wallet_dir)
        elif choice == 'q':
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid choice. Please try again.")
            time.sleep(1)

if __name__ == "__main__":
    main()