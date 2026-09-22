# TeleDrop

Sends images to a Telegram chat/channel via URL, one at a time or in bulk from a text file.

## Files

| File | Purpose |
|---|---|
| `teledrop.py` | The script |
| `config.json` | Your bot token and chat ID |
| `requirements.txt` | Python dependency (`requests`) |
| `.gitignore` | Keeps `config.json` out of version control |

## Setup

```bash
pip install -r requirements.txt
```

Edit `config.json`, replacing both placeholders:

```json
{
  "bot_token": "123456789:AAExampleTokenFromBotFather",
  "chat_id": "-1001234567890"
}
```

- `bot_token` — from [@BotFather](https://t.me/BotFather) on Telegram.
- `chat_id` — your user ID, or a channel/group ID (negative number for groups/channels). Get it by messaging [@userinfobot](https://t.me/userinfobot) or checking your channel's admin API.

## Usage

Single image:
```bash
python teledrop.py "https://example.com/image.jpg"
```

Bulk, from a text file (one URL per line, `#` for comments):
```bash
python teledrop.py urls.txt
```

With a caption (Markdown supported — bold, italic, etc.):
```bash
python teledrop.py urls.txt -c "*New drop* incoming"
```

## Credential resolution order

Highest priority wins:

1. `--token` / `--chat-id` CLI flags
2. `config.json`
3. `TELEDROP_BOT_TOKEN` / `TELEDROP_CHAT_ID` environment variables
4. none set → script exits with an error

You only need one of these. `config.json` is the default path for this setup.

## Behavior notes

- **Rate limits (HTTP 429):** the script reads Telegram's `retry_after` value, waits, and retries automatically — up to 2 retries per image.
- **Broken Markdown in captions:** if Telegram rejects the caption's formatting (`can't parse entities`), the script automatically resends that image as plain text rather than failing it outright.
- **Malformed `config.json`:** the script exits immediately with the JSON parse error rather than silently falling through to env vars — a broken config should be visible, not masked.
- 1 second delay between sends to avoid tripping Telegram's rate limits on bulk jobs.

## Security

`config.json` holds a live bot token. Treat it like a password:

- It's already listed in `.gitignore` — don't remove that line.
- If this token ever ends up in a public repo or chat log, revoke it immediately via @BotFather (`/revoke`) and issue a new one. A token in git history is not fixed by deleting the line in a later commit.
