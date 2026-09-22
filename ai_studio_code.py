#!/usr/bin/env python3
import requests
import time
import os
import sys
import json
import argparse
from tqdm import tqdm

# ==========================================
# CONSTANTS & VERSION
# ==========================================
VERSION = "1.5"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

ASCII_ART = r"""
█████ █████ █     █████ ████  ████   ███  ████ 
  █   █     █     █     █   █ █   █ █   █ █   █
  █   █     █     █     █   █ █   █ █   █ █   █
  █   ████  █     ████  █   █ ████  █   █ ████ 
  █   █     █     █     █   █ █ █   █   █ █    
  █   █     █     █     █   █ █  █  █   █ █    
  █   █████ █████ █████ ████  █   █  ███  █    
"""

BANNER = f"{BLUE}{ASCII_ART}{RESET}          {YELLOW}[ v{VERSION} ] - Telegram Image Automation Tool{RESET}\n"
# ==========================================

class ProgressFile(object):
    """ Wraps a file to show progress with tqdm while reading for upload """
    def __init__(self, filename, mode):
        self.size = os.path.getsize(filename)
        self.file = open(filename, mode)
        self.bar = tqdm(total=self.size, unit='B', unit_scale=True, desc="[↑] Uploading", leave=False)

    def read(self, size=-1):
        data = self.file.read(size)
        self.bar.update(len(data))
        return data

    def close(self):
        self.bar.close()
        self.file.close()

def send_photo_to_telegram(image_url, chat_id, bot_token, caption="", max_retries=2):
    """
    Downloads image with a progress bar, then uploads it with another progress bar.
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    temp_filename = "teledrop_temp_image.jpg"

    # --- 1. DOWNLOAD WITH PROGRESS BAR ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="[↓] Downloading", leave=False) as bar:
            with open(temp_filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    bar.update(len(chunk))
                    f.write(chunk)
    except Exception as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Download error: {e}")
        return False

    # --- 2. UPLOAD WITH PROGRESS BAR ---
    payload = {'chat_id': chat_id}
    if caption:
        if len(caption) > 1024: caption = caption[:1021] + "..."
        payload.update({'caption': caption, 'parse_mode': 'Markdown'})

    success = False
    for attempt in range(max_retries + 1):
        try:
            pf = ProgressFile(temp_filename, 'rb')
            files = {'photo': pf}
            
            res = requests.post(api_url, data=payload, files=files, timeout=60)
            pf.close()
            
            result = res.json()
            if result.get('ok'):
                print(f"{BLUE}[+]{RESET} TeleDrop: Success -> {image_url}")
                success = True
                break
            
            description = result.get('description', '')
            if res.status_code == 429:
                wait = result.get('parameters', {}).get('retry_after', 5)
                time.sleep(wait)
                continue
            
            if "can't parse entities" in description.lower():
                payload.pop('parse_mode', None)
                continue

            print(f"{YELLOW}[-]{RESET} TeleDrop: API Error: {description}")
            break
        except Exception as e:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Connection error: {e}")
            break

    if os.path.exists(temp_filename): os.remove(temp_filename)
    return success

def load_config():
    """ Strictly loads from config.json """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.isfile(config_path):
        print(f"{YELLOW}[-]{RESET} TeleDrop: config.json not found.")
        sys.exit(1)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            token, chat_id = data.get("bot_token"), data.get("chat_id")
            if not token or not chat_id:
                print(f"{YELLOW}[-]{RESET} TeleDrop: Missing keys in config.json")
                sys.exit(1)
            return token, chat_id
    except Exception as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: config.json error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="TeleDrop: Automate image uploads to Telegram.")
    parser.add_argument("target", nargs="?", help="Single image URL or path to a .txt file")
    parser.add_argument("-c", "--caption", help="Custom caption for images", default="")
    parser.add_argument("-v", "--version", action="version", version=f"TeleDrop v{VERSION}")
    
    args = parser.parse_args()

    # Show banner only if we are not just asking for the version
    print(BANNER)

    if not args.target:
        parser.error("the following arguments are required: target")

    BOT_TOKEN, CHAT_ID = load_config()

    if args.target.endswith('.txt') or os.path.isfile(args.target):
        with open(args.target, 'r', encoding='utf-8-sig') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        urls = [args.target]

    print(f"{BLUE}[*]{RESET} TeleDrop: Target Chat -> {CHAT_ID}")
    print(f"{BLUE}[*]{RESET} TeleDrop: Processing {len(urls)} target(s)...\n")

    success_count = 0
    for i, img_url in enumerate(urls):
        if send_photo_to_telegram(img_url, CHAT_ID, BOT_TOKEN, args.caption):
            success_count += 1
        if i < len(urls) - 1:
            time.sleep(1)

    print(f"\n{BLUE}[*]{RESET} TeleDrop: Done! Success: {success_count}, Fail: {len(urls)-success_count}")

if __name__ == "__main__":
    main()