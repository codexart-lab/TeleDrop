# TeleDrop

**TeleDrop** is a lightweight, CLI-based automation tool designed for cybersecurity professionals, OSINT investigators, and red teamers to seamlessly broadcast visual intelligence to Telegram channels and groups.

It supports both single URL uploads and bulk operations via text files, complete with custom Markdown captioning for contextual alerts.

## 🚀 Features

- **Single & Bulk Drops:** Send one image or process hundreds via a `.txt` file.
- **Custom Captions:** Add contextual Markdown-formatted captions to your visual intel.
- **Rate Limit Protection:** Built-in delays, plus automatic wait-and-retry if Telegram returns a 429.
- **Resilient Sends:** If a caption's Markdown is malformed, TeleDrop automatically resends it as plain text instead of failing the whole drop.
- **Comment Support:** Ignore lines in your `.txt` file by starting them with `#`.
- **Clean CLI:** ASCII banner and structured console output.

## 🛠️ Installation

1. Clone the repository or download the files:
```bash
git clone https://github.com/yourusername/teledrop.git
cd teledrop
```

2. Install the required Python dependencies:
```bash
pip install -r requirements.txt
```

3. Edit `config.json` with your bot token and chat ID:
```bash
nano config.json      # Linux / macOS
notepad config.json   # Windows
```

## ⚙️ Configuration

Before running the tool, set your Telegram Bot Token and Chat ID. TeleDrop checks these sources in priority order — the first one it finds wins:

1. **`--token` / `--chat-id` CLI flags**
2. **`config.json`**
```json
{
  "bot_token": "123456789:AAHere_your_real_bot_token_from_BotFather",
  "chat_id": "-1001234567890"
}
```
3. **`TELEDROP_BOT_TOKEN` / `TELEDROP_CHAT_ID` environment variables**

Get a Bot Token from [@BotFather](https://t.me/BotFather). Chat ID can be your Channel username (e.g., `@my_channel`) or the numeric Group/Channel ID.
   * *Note: The bot must be added as an Admin in channels to post messages.*

*(OPSEC Tip: `config.json` is already listed in `.gitignore` — leave it there, and never hardcode credentials directly in `teledrop.py`.)*

## 💻 Usage

### Basic Help
```bash
python teledrop.py -h
```

### Single Image Drop
```bash
python teledrop.py "https://example.com/screenshot.png"
```

### Single Image with Custom Caption
```bash
python teledrop.py "https://example.com/screenshot.png" -c "**[ALERT]** New C2 Infrastructure Detected. See attached screenshot."
```

### Bulk Drop via Text File
Create a `urls.txt` file:
```text
# OSINT Batch 1
https://example.com/img1.png
https://example.com/img2.jpg

# OSINT Batch 2
https://i.imgur.com/abc123.png
```
Run the tool:
```bash
python teledrop.py urls.txt -c "Daily OSINT Drop - Batch 1"
```

## 🔍 How to find your Chat ID
If you need the numeric Chat ID for a private group:
1. Add your bot to the group.
2. Send a message in the group.
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Look for the `"chat":{"id": -100XXXXXXXXXX}` value in the JSON response.

## 📁 Project Files

| File | Purpose |
|---|---|
| `teledrop.py` | The script |
| `config.json` | Your bot token and chat ID (gitignored) |
| `requirements.txt` | Python dependency (`requests`) |
| `.gitignore` | Keeps `config.json` out of version control |
| `LICENSE` | MIT License |

## ⚠️ Disclaimer
This tool is intended for legitimate cybersecurity operations, OSINT reporting, and team communications. Ensure that your usage complies with Telegram's Terms of Service and your organization's security policies. Do not use this tool for spam or malicious distribution.

## 📜 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
