# TeleDrop

TeleDrop is a command-line tool for uploading images to a Telegram channel or group through a Telegram bot. It supports sending a single image or bulk-uploading many at once from a text file, with optional captions and configurable time intervals between requests.

Images are downloaded locally first, then uploaded to Telegram as actual file data — not passed as a URL.

---

## Features

- **Single or bulk uploads** — one image, or hundreds from a `.txt` file
- **Captions** — optional, Markdown-formatted
- **Progress bars** — live download and upload progress via `tqdm`
- **Reliable delivery** — downloads the image itself instead of relying on Telegram to fetch the URL, which avoids host-side blocking
- **Automatic retries** — handles Telegram rate limits and caption formatting errors without failing the whole batch
- **Configurable intervals** — wait a fixed or randomized amount of time between requests to avoid rate-limit bans (default: 2 seconds)
- **Config-only credentials** — bot token and chat ID are read from `config.json` only, kept out of shell history and version control

---

## Installation

1. Clone the repository *(replace with your actual repo URL)*:
```bash
git clone https://github.com/codexart-lab/TeleDrop.git
cd TeleDrop
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```
Activate a virtual environment:
```bash
source venv/bin/activate      # Linux / macOS
```
For Windows
```bash
venv\Scripts\activate         # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Configuration

Create/edit `config.json` in the same folder as the script:

```bash
nano config.json      # Linux / macOS
notepad config.json   # Windows
```

```json
{
  "bot_token": "123456789:AAHere_your_real_bot_token_from_BotFather",
  "chat_id": "-1001234567890"
}
```

- **Bot Token** — get one from [@BotFather](https://t.me/BotFather).
- **Chat ID** — numeric ID (e.g. `-100...` for a group/channel) or a public channel username (e.g. `@my_channel`).
- The bot must be added as an **Administrator** of the channel to post there.

---

## Usage

### Help & Version
```bash
python teledrop.py -h
python teledrop.py --version
```

### Single Image
```bash
python teledrop.py "https://example.com/image.jpg"
```

### Single Image with Caption
```bash
python teledrop.py "https://example.com/image.jpg" -c "Caption here"
```

### Bulk Upload from Text File
```bash
python teledrop.py urls.txt -c "Batch caption"
```

`urls.txt` format — one URL per line, `#` for comments:
```text
# Batch 1
https://example.com/img1.png
https://example.com/img2.jpg
```

---

## Time Intervals

TeleDrop waits between requests so bulk uploads don't trigger Telegram's rate limits or look bot-like.

### Default (no flags needed)
Waits **2 seconds** between every download/upload:
```bash
python teledrop.py urls.txt
```

### Fixed interval
Set any number of seconds with `-i` / `--interval`:
```bash
python teledrop.py urls.txt -i 5        # 5 seconds between requests
python teledrop.py urls.txt -i 0.5     # half a second
python teledrop.py urls.txt -i 0       # no waiting (not recommended)
```

### Randomized interval (recommended)
Human-like, unpredictable pacing using `--min-interval` and `--max-interval` (both must be used together):
```bash
python teledrop.py urls.txt --min-interval 2 --max-interval 6
```

### Interval behavior
- The **first** image is sent immediately — waiting starts from the second request.
- The interval applies between **downloads and uploads** alike.
- If Telegram returns a rate-limit (`429`) response, the script additionally waits for the server-specified `retry_after` time.
- Invalid values (negative numbers, `--min-interval` without `--max-interval`, min greater than max) exit with an error message.

---

## Project Files

| File | Purpose |
|---|---|
| `teledrop.py` | The script |
| `config.json` | Bot token and chat ID (gitignored) |
| `requirements.txt` | Dependencies: `requests`, `tqdm` |
| `.gitignore` | Keeps `config.json` and `venv/` out of version control |
| `LICENSE` | MIT License |

## License
MIT — see the [LICENSE](LICENSE) file.
