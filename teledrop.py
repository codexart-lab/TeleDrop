#!/usr/bin/env python3
import requests
import time
import os
import sys
import json
import argparse

# ==========================================
# BANNER & COLORS
# ==========================================
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

ASCII_ART = r"""
  _____    _      _____ 
 |_   _|  | |    |  __ \
   | | ___| | ___| |  | | ___  ___  ___ 
   | |/ _ \ |/ _ \ |  | |/ _ \/ _ \/ __|
   | |  __/ |  __/ |__| |  __/  __/\__ \
   |_|\___|_|\___|_____/ \___|\___||___/
"""

BANNER = f"{BLUE}{ASCII_ART}{RESET}          {YELLOW}[ v1.1 ] - Telegram Image Automation Tool{RESET}\n"
# ==========================================


def send_photo_to_telegram(image_url, chat_id, bot_token, caption="", max_retries=2):
    """
    Sends an image to a Telegram chat/channel via URL.
    Handles: non-JSON responses, Markdown parse failures (auto-retries as
    plain text), and 429 rate-limit responses (waits retry_after seconds).
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    payload = {
        'chat_id': chat_id,
        'photo': image_url,
    }

    if caption:
        if len(caption) > 1024:
            print("[!] Warning: Caption exceeds 1024 characters. Truncating.")
            caption = caption[:1021] + "..."
        payload['caption'] = caption
        payload['parse_mode'] = 'Markdown'

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(api_url, data=payload, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Network error for {image_url}: {e}")
            return False

        # Bug fix: response.json() can raise ValueError/JSONDecodeError,
        # which is NOT a RequestException and was previously uncaught.
        try:
            result = response.json()
        except ValueError:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Non-JSON response for {image_url} "
                  f"(HTTP {response.status_code}). Raw: {response.text[:200]}")
            return False

        if result.get('ok'):
            print(f"{BLUE}[+]{RESET} TeleDrop: Successfully sent -> {image_url}")
            return True

        description = result.get('description', '')
        params = result.get('parameters', {}) or {}
        retry_after = params.get('retry_after')

        # Bug fix: 429 rate-limit was previously treated as a plain failure.
        if response.status_code == 429 and retry_after and attempt < max_retries:
            print(f"{YELLOW}[!]{RESET} TeleDrop: Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        # Bug fix: Markdown parse errors previously failed the send outright,
        # even though the image itself was valid. Retry once as plain text.
        if "can't parse entities" in description.lower() and 'parse_mode' in payload and attempt < max_retries:
            print(f"{YELLOW}[!]{RESET} TeleDrop: Caption Markdown invalid, "
                  f"resending as plain text -> {image_url}")
            payload.pop('parse_mode', None)
            continue

        print(f"{YELLOW}[-]{RESET} TeleDrop: Failed to send -> {image_url}")
        print(f"    API Error: {description}")
        return False

    return False


def load_config():
    """
    Loads bot_token / chat_id from config.json, located in the same
    directory as this script. Returns {} if the file doesn't exist.
    Exits with a clear error if it exists but is malformed — silently
    ignoring a broken config would just push the failure downstream.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    if not os.path.isfile(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: config.json is not valid JSON: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Couldn't read config.json: {e}")
        sys.exit(1)


def load_urls_from_file(file_path):
    """
    Reads URLs from a text file, ignoring empty lines and comments.
    """
    if not os.path.isfile(file_path):
        print(f"{YELLOW}[-]{RESET} TeleDrop: Error: File '{file_path}' not found.")
        sys.exit(1)

    # Bug fix: 'utf-8' left a leading \ufeff BOM character on the first line
    # for files saved by Windows editors, silently breaking the first URL.
    # 'utf-8-sig' strips the BOM if present.
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not urls:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Error: '{file_path}' contained no valid URLs.")
        sys.exit(1)

    return urls


def main():
    print(BANNER)

    # ==========================================
    # CONFIGURATION
    # Resolution order (highest priority first):
    #   1. --token / --chat-id CLI flags
    #   2. config.json (bot_token / chat_id keys)
    #   3. TELEDROP_BOT_TOKEN / TELEDROP_CHAT_ID env vars
    #   4. placeholder default (triggers the error below)
    # ==========================================
    config = load_config()

    BOT_TOKEN = config.get("bot_token") or os.environ.get("TELEDROP_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    CHAT_ID = config.get("chat_id") or os.environ.get("TELEDROP_CHAT_ID", "YOUR_CHAT_ID_HERE")

    DELAY_BETWEEN_REQUESTS = 1  # Seconds (Prevents API rate-limit bans)
    # ==========================================

    parser = argparse.ArgumentParser(description="TeleDrop: Automate image uploads to Telegram via URL.")
    parser.add_argument("target", help="Single image URL or path to a .txt file containing URLs")
    parser.add_argument("-c", "--caption", help="Custom caption for the images (Supports Markdown)", default="")
    parser.add_argument("--token", help="Override bot token (or set in config.json / TELEDROP_BOT_TOKEN env var)", default=None)
    parser.add_argument("--chat-id", help="Override chat ID (or set in config.json / TELEDROP_CHAT_ID env var)", default=None)

    args = parser.parse_args()
    target = args.target
    caption = args.caption

    if args.token:
        BOT_TOKEN = args.token
    if args.chat_id:
        CHAT_ID = args.chat_id

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print(f"{YELLOW}[-]{RESET} TeleDrop: Error: No token/chat_id found. Set them in "
              f"config.json, via TELEDROP_BOT_TOKEN/TELEDROP_CHAT_ID env vars, or --token/--chat-id flags.")
        sys.exit(1)

    if target.endswith('.txt') or os.path.isfile(target):
        urls = load_urls_from_file(target)
        print(f"{BLUE}[*]{RESET} TeleDrop: Loaded {len(urls)} URLs from '{target}'")
    else:
        urls = [target]
        print(f"{BLUE}[*]{RESET} TeleDrop: Processing single URL -> {target}")

    print(f"{BLUE}[*]{RESET} TeleDrop: Target Chat ID -> {CHAT_ID}")
    if caption:
        print(f"{BLUE}[*]{RESET} TeleDrop: Custom Caption -> {caption[:50]}{'...' if len(caption) > 50 else ''}\n")
    else:
        print()

    success_count = 0
    fail_count = 0

    for i, img_url in enumerate(urls):
        if send_photo_to_telegram(img_url, CHAT_ID, BOT_TOKEN, caption):
            success_count += 1
        else:
            fail_count += 1

        if i < len(urls) - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n{BLUE}[*]{RESET} TeleDrop: Upload Complete!")
    print(f"    Successes: {success_count}")
    print(f"    Failures:  {fail_count}")


if __name__ == "__main__":
    main()
