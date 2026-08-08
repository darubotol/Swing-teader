"""
telegram_bot.py
Sends the daily summary (and the full report as a file) to your Telegram chat
via the Bot API. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars
(set as GitHub Actions secrets — see README.md for how to get these).
"""

import requests
import config


def send_message(text: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram_bot] Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — skipping send.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram hard limit is 4096 chars per message — split if needed.
    chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)] or [text]
    for chunk in chunks:
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
        })
        if resp.status_code != 200:
            print(f"[telegram_bot] Failed to send message: {resp.status_code} {resp.text}")


def send_document(filepath: str, caption: str = "") -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram_bot] Missing credentials — skipping document send.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption},
            files={"document": f},
        )
    if resp.status_code != 200:
        print(f"[telegram_bot] Failed to send document: {resp.status_code} {resp.text}")