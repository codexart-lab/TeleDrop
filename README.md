# TeleDrop

**TeleDrop** is a lightweight, CLI-based automation tool designed for cybersecurity professionals, OSINT investigators, and red teamers to seamlessly broadcast visual intelligence to Telegram channels and groups. 

It supports both single URL uploads and bulk operations via text files, complete with custom Markdown captioning for contextual alerts.

## 🚀 Features

- **Single & Bulk Drops:** Send one image or process hundreds via a `.txt` file.
- **Custom Captions:** Add contextual Markdown-formatted captions to your visual intel.
- **Rate Limit Protection:** Built-in delays to prevent Telegram API bans during bulk ops.
- **Comment Support:** Ignore lines in your `.txt` file by starting them with `#`.
- **Clean CLI:** Beautiful ASCII banner and structured console output.

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

## ⚙️ Configuration

Before running the tool, you must configure your Telegram Bot Token and Chat ID.

1. Open `teledrop.py` in a text editor.
2. Replace `YOUR_BOT_TOKEN_HERE` with your actual Bot Token (get one from [@BotFather](https://t.me/BotFather)).
3. Replace `YOUR_CHAT_ID_HERE` with your Channel username (e.g., `@my_channel`) or the numeric Group/Channel ID.
   * *Note: The bot must be added as an Admin in channels to post messages.*

*(OPSEC Tip: For better security, uncomment the `os.getenv()` lines in the script and pass your tokens as environment variables instead of hardcoding them).*

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

## ⚠️ Disclaimer
This tool is intended for legitimate cybersecurity operations, OSINT reporting, and team communications. Ensure that your usage complies with Telegram's Terms of Service and your organization's security policies. Do not use this tool for spam or malicious distribution.

## 📜 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
