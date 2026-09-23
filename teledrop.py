#!/usr/bin/env python3
import requests
import time
import os
import sys
import json
import random
import argparse
import tempfile

try:
    from tqdm import tqdm
except ImportError:
    print("Missing dependency: tqdm. Run: pip install -r requirements.txt")
    sys.exit(1)

VERSION = "1.3"

# ==========================================
# BANNER & COLORS
# ==========================================
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

# Default seconds between requests (uploads AND downloads)
DEFAULT_INTERVAL = 2.0

# Browser-like User-Agent. Telegram's own server-side URL fetcher gets
# blocked by anti-hotlinking rules on hosts like ibb.co (that's what
# causes "Bad Request: failed to get HTTP URL content"). Downloading
# the image ourselves with this header, then uploading the bytes
# directly, avoids relying on Telegram's fetcher at all.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def get_wait_time(min_delay, max_delay):
    """
    Returns the next wait time in seconds. If min_delay == max_delay,
    returns the fixed value; otherwise picks a random value in the
    inclusive range [min_delay, max_delay] for human-like pacing.
    """
    if min_delay >= max_delay:
        return min_delay
    return random.uniform(min_delay, max_delay)


def sleep_with_message(seconds):
    """Sleeps for the given seconds, printing a small notice."""
    if seconds > 0:
        print(f"{BLUE}[*]{RESET} TeleDrop: Waiting {seconds:.1f}s before next request...")
        time.sleep(seconds)


def download_image(image_url, dest_dir):
    """
    Downloads image_url into dest_dir with a browser User-Agent and a
    live progress bar. Returns the local file path, or None on failure.
    """
    headers = {"User-Agent": BROWSER_USER_AGENT}
    try:
        response = requests.get(image_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Download failed for {image_url}: {e}")
        return None

    total = int(response.headers.get("content-length", 0))
    filename = os.path.basename(image_url.split("?")[0]) or f"image_{int(time.time()*1000)}.jpg"
    local_path = os.path.join(dest_dir, filename)

    try:
        with open(local_path, "wb") as f, tqdm(
            total=total if total > 0 else None,
            unit="B", unit_scale=True, unit_divisor=1024,
            desc=f"{BLUE}[\u2193] Download{RESET}", leave=False,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
    except OSError as e:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Couldn't write temp file for {image_url}: {e}")
        return None

    return local_path


def send_photo_to_telegram(local_path, chat_id, bot_token, caption="", max_retries=2):
    """
    Uploads a local image file to Telegram as multipart form data (not
    by URL). Handles: non-JSON responses, Markdown parse failures
    (auto-retries as plain text), and 429 rate-limit responses.
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    data = {'chat_id': chat_id}
    if caption:
        if len(caption) > 1024:
            print("[!] Warning: Caption exceeds 1024 characters. Truncating.")
            caption = caption[:1021] + "..."
        data['caption'] = caption
        data['parse_mode'] = 'Markdown'

    for attempt in range(max_retries + 1):
        file_size = os.path.getsize(local_path)
        try:
            with open(local_path, "rb") as f, tqdm.wrapattr(
                f, "read", total=file_size,
                unit="B", unit_scale=True, unit_divisor=1024,
                desc=f"{BLUE}[\u2191] Upload{RESET}", leave=False,
            ) as wrapped_file:
                files = {'photo': (os.path.basename(local_path), wrapped_file)}
                response = requests.post(api_url, data=data, files=files, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Network error uploading {os.path.basename(local_path)}: {e}")
            return False

        try:
            result = response.json()
        except ValueError:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Non-JSON response for {os.path.basename(local_path)} "
                  f"(HTTP {response.status_code}). Raw: {response.text[:200]}")
            return False

        if result.get('ok'):
            print(f"{BLUE}[+]{RESET} TeleDrop: Successfully sent -> {os.path.basename(local_path)}")
            return True

        description = result.get('description', '')
        params = result.get('parameters', {}) or {}
        retry_after = params.get('retry_after')

        if response.status_code == 429 and retry_after and attempt < max_retries:
            print(f"{YELLOW}[!]{RESET} TeleDrop: Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        if "can't parse entities" in description.lower() and 'parse_mode' in data and attempt < max_retries:
            print(f"{YELLOW}[!]{RESET} TeleDrop: Caption Markdown invalid, resending as plain text.")
            data.pop('parse_mode', None)
            continue

        print(f"{YELLOW}[-]{RESET} TeleDrop: Failed to send -> {os.path.basename(local_path)}")
        print(f"    API Error: {description}")
        return False

    return False


def load_config():
    """
    Loads bot_token / chat_id from config.json, located in the same
    directory as this script. This is now the ONLY credential source —
    no CLI flags, no env vars — to keep secrets out of shell history
    and process listings entirely.
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

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not urls:
        print(f"{YELLOW}[-]{RESET} TeleDrop: Error: '{file_path}' contained no valid URLs.")
        sys.exit(1)

    return urls


def main():
    print(BANNER)

    config = load_config()
    BOT_TOKEN = config.get("bot_token", "YOUR_BOT_TOKEN_HERE")
    CHAT_ID = config.get("chat_id", "YOUR_CHAT_ID_HERE")

    parser = argparse.ArgumentParser(description="TeleDrop: Automate image uploads to Telegram via URL.")
    parser.add_argument("target", help="Single image URL or path to a .txt file containing URLs")
    parser.add_argument("-c", "--caption", help="Custom caption for the images (Supports Markdown)", default="")
    parser.add_argument("-i", "--interval", type=float, default=DEFAULT_INTERVAL,
                        help=f"Fixed seconds to wait between requests (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--min-interval", type=float, default=None, metavar="SEC",
                        help="Minimum seconds for randomized intervals (requires --max-interval)")
    parser.add_argument("--max-interval", type=float, default=None, metavar="SEC",
                        help="Maximum seconds for randomized intervals (requires --min-interval)")
    parser.add_argument("--version", action="version", version=f"TeleDrop v{VERSION}")

    args = parser.parse_args()
    target = args.target
    caption = args.caption

    # --- Time interval resolution ---
    if args.min_interval is not None or args.max_interval is not None:
        if args.min_interval is None or args.max_interval is None:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Error: Use both --min-interval and --max-interval together.")
            sys.exit(1)
        if args.min_interval < 0 or args.max_interval < 0:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Error: Intervals must be >= 0.")
            sys.exit(1)
        if args.min_interval > args.max_interval:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Error: --min-interval cannot exceed --max-interval.")
            sys.exit(1)
        min_delay, max_delay = args.min_interval, args.max_interval
        interval_desc = f"random {min_delay:.1f}-{max_delay:.1f}s"
    else:
        if args.interval < 0:
            print(f"{YELLOW}[-]{RESET} TeleDrop: Error: --interval must be >= 0.")
            sys.exit(1)
        min_delay = max_delay = args.interval
        interval_desc = f"fixed {args.interval:.1f}s"

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print(f"{YELLOW}[-]{RESET} TeleDrop: Error: No bot_token/chat_id found. Set both in config.json.")
        sys.exit(1)

    if target.endswith('.txt') or os.path.isfile(target):
        urls = load_urls_from_file(target)
        print(f"{BLUE}[*]{RESET} TeleDrop: Loaded {len(urls)} URLs from '{target}'")
    else:
        urls = [target]
        print(f"{BLUE}[*]{RESET} TeleDrop: Processing single URL -> {target}")

    print(f"{BLUE}[*]{RESET} TeleDrop: Target Chat ID -> {CHAT_ID}")
    print(f"{BLUE}[*]{RESET} TeleDrop: Interval -> {interval_desc}")
    if caption:
        print(f"{BLUE}[*]{RESET} TeleDrop: Custom Caption -> {caption[:50]}{'...' if len(caption) > 50 else ''}\n")
    else:
        print()

    success_count = 0
    fail_count = 0

    with tempfile.TemporaryDirectory(prefix="teledrop_") as tmp_dir:
        for i, img_url in enumerate(urls):
            # Wait between requests: paces uploads AND downloads,
            # including after rate-limit retries. Skipped before the
            # very first image so the run starts immediately.
            if i > 0:
                sleep_with_message(get_wait_time(min_delay, max_delay))

            local_path = download_image(img_url, tmp_dir)
            if local_path is None:
                fail_count += 1
                continue

            try:
                if send_photo_to_telegram(local_path, CHAT_ID, BOT_TOKEN, caption):
                    success_count += 1
                else:
                    fail_count += 1
            finally:
                try:
                    os.remove(local_path)
                except OSError:
                    pass

    print(f"\n{BLUE}[*]{RESET} TeleDrop: Upload Complete!")
    print(f"    Successes: {success_count}")
    print(f"    Failures:  {fail_count}")


if __name__ == "__main__":
    main()
