#!/usr/bin/env python3
"""
Helper: list the Telegram chat IDs of everyone who has messaged the bot.

Usage:
  1. Put your token into config.json (telegram_token).
  2. Both users open the bot in Telegram and press Start / send any message.
  3. Run:  python3 get_chat_ids.py
  4. Copy the printed IDs into config.json -> "chat_ids".
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
    cfg = json.load(f)

token = cfg["telegram_token"]
url = f"https://api.telegram.org/bot{token}/getUpdates"
data = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())

if not data.get("ok"):
    print("Telegram error:", data)
    raise SystemExit(1)

seen = {}
for upd in data.get("result", []):
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat = msg.get("chat")
    if chat:
        seen[chat["id"]] = chat.get("username") or chat.get("first_name") or "?"

if not seen:
    print("No messages yet. Ask both users to press Start / send a message to the bot, then re-run.")
else:
    print("Found chats (add these ids to config.json -> chat_ids):")
    for cid, who in seen.items():
        print(f"  {cid}   ({who})")
    print()
    print("chat_ids:", list(seen.keys()))
