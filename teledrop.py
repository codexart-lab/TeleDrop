#!/usr/bin/env python3
import requests
import time
import os
import sys
import argparse

BANNER = """
  _____    _      _____                 
 |_   _|  | |    |  __ \                
   | | ___| | ___| |  | | ___  ___  ___ 
   | |/ _ \ |/ _ \ |  | |/ _ \/ _ \/ __|
   | |  __/ |  __/ |__| |  __/  __/\__ \\
   |_|\___|_|\___|_____/ \___|\___||___/
         [ v1.0 ] - Cybersecurity Image Broadcaster
"""

def send_photo_to_telegram(image_url, chat_id, bot_token, caption=""):
    """
    Sends an image to a Telegram chat/channel via URL.
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    payload = {
        'chat_id': chat_id,
        'photo': image_url,
        'parse_mode': 'Markdown'
    }
    
    # Add caption if provided (Telegram limits captions to 1024 characters)
    if caption:
        if len(caption) > 1024:
            print("[!] Warning: Caption exceeds 1024 characters. Truncating.")
            caption = caption[:1021] + "..."
        payload['caption'] = caption
    
    try:
        response = requests.post(api_url, data=payload, timeout=15)
        result = response.json()
        
        if result.get('ok'):
            print(f"[+] TeleDrop: Successfully sent -> {image_url}")
            return True
        else:
            print(f"[-] TeleDrop: Failed to send -> {image_url}")
            print(f"    API Error: {result.get('description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[-] TeleDrop: Network error for {image_url}: {e}")
        return False

def load_urls_from_file(file_path):
    """
    Reads URLs from a text file, ignoring empty lines and comments.
    """
    if not os.path.isfile(file_path):
        print(f"[-] TeleDrop: Error: File '{file_path}' not found.")
        sys.exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return urls

def main():
    print(BANNER)

    # ==========================================
    # CONFIGURATION
    # ==========================================
    # For better OPSEC, use environment variables:
    # BOT_TOKEN = os.getenv("TELEDROP_BOT_TOKEN")
    # CHAT_ID = os.getenv("TELEDROP_CHAT_ID")
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"       
    CHAT_ID = "YOUR_CHAT_ID_HERE"           
    
    DELAY_BETWEEN_REQUESTS = 1  # Seconds (Prevents API rate-limit bans)
    # ==========================================

    parser = argparse.ArgumentParser(description="TeleDrop: Covertly upload images to Telegram via URL.")
    parser.add_argument("target", help="Single image URL or path to a .txt file containing URLs")
    parser.add_argument("-c", "--caption", help="Custom caption for the images (Supports Markdown)", default="")
    
    args = parser.parse_args()
    target = args.target
    caption = args.caption

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("[-] TeleDrop: Error: Please configure your BOT_TOKEN and CHAT_ID in the script.")
        sys.exit(1)

    # Determine if the input is a file or a direct URL
    if target.endswith('.txt') or os.path.isfile(target):
        urls = load_urls_from_file(target)
        print(f"[*] TeleDrop: Loaded {len(urls)} URLs from '{target}'")
    else:
        urls = [target]
        print(f"[*] TeleDrop: Processing single URL -> {target}")

    print(f"[*] TeleDrop: Target Chat ID -> {CHAT_ID}")
    if caption:
        print(f"[*] TeleDrop: Custom Caption -> {caption[:50]}{'...' if len(caption)>50 else ''}\n")
    else:
        print()
    
    success_count = 0
    fail_count = 0

    for img_url in urls:
        if send_photo_to_telegram(img_url, CHAT_ID, BOT_TOKEN, caption):
            success_count += 1
        else:
            fail_count += 1
            
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n[*] TeleDrop: Upload Complete!")
    print(f"    Successes: {success_count}")
    print(f"    Failures:  {fail_count}")

if __name__ == "__main__":
    main()
