#!/usr/bin/env python3
"""
Cavo Zoe Seaside Hotel — room availability monitor.

Polls the hidden WebHotelier /avl JSON endpoint for the configured stay and
sends a Telegram alert to every configured chat as soon as a room frees up.

No third-party dependencies — standard library only.
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
STATE_PATH = os.path.join(HERE, "state.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    # Env overrides let secrets stay out of the repo (used by GitHub Actions).
    env_token = os.environ.get("TELEGRAM_TOKEN")
    if env_token:
        cfg["telegram_token"] = env_token.strip()

    env_chats = os.environ.get("CHAT_IDS")
    if env_chats:
        cfg["chat_ids"] = [c.strip() for c in env_chats.split(",") if c.strip()]

    for key in ("CHECKIN", "NIGHTS", "ADULTS", "ROOMS", "CHILDREN"):
        val = os.environ.get(key)
        if val:
            k = key.lower()
            cfg[k] = val if key == "CHECKIN" else int(val)

    return cfg


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"available": False, "last_notified": 0}


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def build_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA)]
    return opener


def fetch_availability(cfg):
    """Return parsed availability dict, or raise on network/parse error."""
    base = cfg["base_url"].rstrip("/")
    checkin = cfg["checkin"]
    nights = cfg["nights"]
    adults = cfg["adults"]
    rooms = cfg["rooms"]
    children = cfg.get("children", 0)

    opener = build_opener()

    # 1) Hit the search page first so the session cookie is set.
    home = f"{base}/?checkin={checkin}&rooms={rooms}&nights={nights}&adults={adults}"
    opener.open(urllib.request.Request(home), timeout=30).read()

    # 2) POST the availability query to the JSON endpoint.
    body = urllib.parse.urlencode({
        "fromd": checkin,
        "nights": nights,
        "adults": adults,
        "rooms": rooms,
        "children": children,
    }).encode()
    req = urllib.request.Request(
        f"{base}/avl",
        data=body,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": home,
            "Accept": "application/json, text/javascript, */*",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    raw = opener.open(req, timeout=30).read().decode("utf-8", "replace")
    return json.loads(raw)


def parse_rooms(html):
    """Extract (name, price, bookable) for every room in the result table.

    Each room block (<tr class="room">) contains one or more rate rows shaped
    like <tr data-status="AVL" data-price="729" ...>. The rate-row status is the
    reliable signal for the requested stay:
        AVL -> bookable for the whole stay
        SS  -> sold out / stop-sell
    (data-so is unrelated to availability and is ignored.)
    """
    results = []
    blocks = re.split(r'<tr class="room">', html)[1:]
    for block in blocks:
        name_m = re.search(r'class="name"[^>]*>([^<]+)<', block)
        name = name_m.group(1).strip() if name_m else "Room"

        avl_prices = []
        for row in re.finditer(r'<tr\s+data-status="([^"]+)"[^>]*'
                               r'data-price="(\d+)"', block):
            status, price = row.group(1), int(row.group(2))
            if status.upper() == "AVL":
                avl_prices.append(price)

        bookable = bool(avl_prices)
        best_price = min(avl_prices) if avl_prices else None
        results.append({"name": name, "bookable": bookable, "price": best_price})
    return results


def evaluate(avl):
    """Return (available: bool, available_rooms: list)."""
    html = avl.get("html", "")
    price_check = avl.get("price_check") or {}
    best = price_check.get("best") or 0

    rooms = parse_rooms(html)
    available_rooms = [r for r in rooms if r["bookable"]]

    # Primary signals (any one is enough):
    #  - a bookable rate exists (data-so="0")
    #  - the engine reports a best bookable price > 0
    available = bool(available_rooms) or best > 0
    return available, available_rooms


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(url, data=body)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def notify_all(cfg, text):
    token = cfg["telegram_token"]
    ok = 0
    for chat_id in cfg["chat_ids"]:
        try:
            res = send_telegram(token, str(chat_id), text)
            if res.get("ok"):
                ok += 1
            else:
                log(f"Telegram error for {chat_id}: {res}")
        except Exception as e:
            log(f"Telegram send failed for {chat_id}: {e}")
    return ok


def build_message(cfg, available_rooms):
    checkin = cfg["checkin"]
    nights = cfg["nights"]
    link = (f"{cfg['base_url'].rstrip('/')}/?checkin={checkin}"
            f"&rooms={cfg['rooms']}&nights={nights}&adults={cfg['adults']}")
    lines = ["🏨 <b>Освободился номер в Cavo Zoe!</b>",
             f"Заезд <b>{checkin}</b>, ночей: <b>{nights}</b>, "
             f"гостей: {cfg['adults']}"]
    if available_rooms:
        lines.append("")
        lines.append("Доступны:")
        for r in available_rooms:
            price = f" — от {r['price']} EUR" if r.get("price") else ""
            lines.append(f"• {r['name']}{price}")
    lines.append("")
    lines.append(f'👉 <a href="{link}">Забронировать сейчас</a>')
    lines.append("⚡️ Успей — номер могут забрать за минуты.")
    return "\n".join(lines)


def main():
    cfg = load_config()
    if "PUT-YOUR" in cfg.get("telegram_token", "") or not cfg.get("chat_ids"):
        log("Config not filled in yet (telegram_token / chat_ids). Skipping.")
        return 0

    state = load_state()
    remind_after = cfg.get("remind_after_seconds", 1800)  # re-alert every 30 min

    try:
        avl = fetch_availability(cfg)
    except Exception as e:
        log(f"Fetch error: {e}")
        return 1

    available, available_rooms = evaluate(avl)
    now = int(time.time())

    if available:
        rising_edge = not state.get("available")
        stale = now - state.get("last_notified", 0) >= remind_after
        if rising_edge or stale:
            names = ", ".join(r["name"] for r in available_rooms) or "room"
            log(f"AVAILABLE -> notifying ({names})")
            sent = notify_all(cfg, build_message(cfg, available_rooms))
            state["last_notified"] = now
            log(f"Notified {sent}/{len(cfg['chat_ids'])} chats")
        else:
            log("Still available, already notified recently.")
        state["available"] = True
    else:
        if state.get("available"):
            log("Back to sold out.")
        else:
            log("Sold out (no change).")
        state["available"] = False

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
