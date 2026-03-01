import requests
import json
import time
import os
from datetime import datetime
import config
import pycountry
import phonenumbers
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# ---------- persistence helpers ----------
def load_sent_ids(path=config.SENT_DB_PATH):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_ids(ids, path=config.SENT_DB_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(ids), f)
    except Exception as e:
        print("[SENTDB] save error:", e)

# ---------- persistence helpers --------
def load_sent_messages(path=config.SENT_DB_PATH):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ডাটা যদি লিস্ট হয়, তবে সেটিকে খালি ডিকশনারিতে রূপান্তর করুন
                if isinstance(data, list):
                    return {}
                return data
        except Exception:
            return {}
    return {}

def save_sent_messages(messages, path=config.SENT_DB_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f)
    except Exception as e:
        print("[SENTDB] save error:", e)

def load_rr_state(path=config.RR_STATE_PATH):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"next_index": 0}
    return {"next_index": 0}

def save_rr_state(state, path=config.RR_STATE_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print("[RR] save error:", e)

# ---------- telegram send helper (per-bot) ----------
def send_with_bot(token, chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        # reply_markup এখন একটি ডিকশনারি, তাই সরাসরি JSON এ রূপান্তর করা যাবে
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json().get("result").get("message_id")
        else:
            print("[TG] HTTP", r.status_code, r.text[:300])
            return None
    except Exception as e:
        print("[TG] Exception:", e)
        return None

# ---------- telegram delete helper ----------
def delete_message_with_bot(token, chat_id, message_id):
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print("[TG] Delete Exception:", e)
        return False

# ---------- formatting & masking ----------
def mask_number(number: str) -> str:
    if not number or len(number) <= 8:
        return number
    return number[:5] + "***" + number[-3:]

# ২. কান্ট্রি কোড থেকে পতাকা (Emoji) তৈরি করার ফাংশন
def country_code_to_emoji(code):
    if not code:
        return "🏳️"
    
    # কোডটিকে ক্লিন করা: স্পেস মুছে ফেলা এবং বড় হাতের অক্ষরে রূপান্তর
    code = str(code).strip().upper() 
    
    # কান্ট্রি কোড ম্যাপ (API তে কান্ট্রি কোড বা নাম যা-ই আসুক, তাকে সঠিক কোডে রূপান্তর করা)
    aliases = {
        "UK": "GB",
        "EN": "GB",
        "VN": "VN",
        "VIETNAM": "VN", # Vietnamese
        "CH": "CH",      # Switzerland
        "US": "US",
        "CN": "CN",
        "RU": "RU"
        # যদি অন্য কোনো দেশের পতাকা ভুল আসে, এখানে "ভুল নাম": "সঠিক কোড" ফরম্যাটে যোগ করুন
    }
    
    # aliases এ থাকলে তা নেওয়া, নাহলে মূল কোডটি ব্যবহার করা
    code = aliases.get(code, code)
    
    # যদি কোডটি ২ অক্ষরের না হয়, তবে সাদা পতাকা দেখানো
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    
    # সঠিক পতাকার ইমোজিতে রূপান্তর করা
    return "".join(chr(127397 + ord(c)) for c in code)

def format_item(it):
    # ===== RAW DATA =====
    platform_raw = str(it.get("platform", "WS")).upper()
    number_raw = str(it.get("number", "")).replace("+", "").strip()

    # ===== SERVICE SHORT MAP =====
    service_map = {
        "WHATSAPP": "WS",
        "TELEGRAM": "TG",
        "WS": "WS",
        "TG": "TG"
    }
    service = service_map.get(platform_raw, platform_raw[:2])

    # ===== COUNTRY DETECT FROM NUMBER ONLY =====
    country_code = "UN"
    try:
        parsed = phonenumbers.parse("+" + number_raw, None)
        region_code = phonenumbers.region_code_for_number(parsed)
        if region_code:
            country = pycountry.countries.get(alpha_2=region_code)
            if country:
                country_code = country.alpha_2
    except:
        pass

    # ===== FLAG =====
    flag = country_code_to_emoji(country_code)

    # ===== NUMBER FORMAT =====
    # +CC + delete next 3 digits → AWM
    if len(number_raw) > 5:
        formatted_number = f"+{number_raw[:2]}AWM{number_raw[5:]}"
    else:
        formatted_number = f"+{number_raw}"

    language = "English"

    # ===== ONE LINE FINAL FORMAT =====
    # এখানে formatted_number এবং #language এর মাঝে একটি স্পেস ' ' যোগ করা হয়েছে
    return f"#{service} #{country_code}{flag} {formatted_number} #{language}"

def get_buttons(it):
    # API থেকে OTP নেওয়া
    otp = it.get("otp", "----")
    
    # বাটনগুলোর ডিকশনারি তৈরি
    keyboard = [
        [
            # OTP বাটন (কপি টেক্সট সহ এবং রঙিন)
            {
                "text": f"📋 {otp}", 
                "copy_text": {"text": str(otp)},
                "style": "danger" # <--- বাটনটি লাল রঙের হবে
            }
        ],
        [
            # URL বাটন - রঙিন স্টাইল সহ
            {
                "text": "📞 Number Channel", 
                "url": "https://t.me/Awm_Proxy_Store_bot",
                "style": "primary" # <--- নীল
            },
            {
                "text": "🤖 AWM Bot", 
                "url": "https://t.me/AWM_NUMBER_BOT",
                "style": "success" # <--- সবুজ
            }
        ]
    ]
    
    # সরাসরি ডিকশনারিটি পাঠান
    return {"inline_keyboard": keyboard}

# ---------- fetch from container ----------
def fetch_all_items():
    headers = {"x-api-key": config.CONTAINER_API_KEY}
    try:
        r = requests.get(config.CONTAINER_URL, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print("[API] bad status:", r.status_code, r.text[:300])
            return []
    except Exception as e:
        print("[API] error:", e)
        return []

# ---------- round-robin logic ----------
def choose_next_bot(rr_state, num_bots):
    idx = rr_state.get("next_index", 0) % max(1, num_bots)
    # update for next time
    rr_state["next_index"] = (idx + 1) % max(1, num_bots)
    return idx

# ---------- main loop ----------
# ---------- main loop ----------
# ---------- main loop ----------
def run_loop():
    # sent_items dictionary use korbo id ar time store korar jonno
    sent_items = load_sent_messages()
    rr_state = load_rr_state()
    print("[RUN] loaded sent items count:", len(sent_items))
    print("[RUN] loaded rr_state:", rr_state)

    # --- NEW LOGIC: Initialize with current timestamp to skip old OTPs ---
    # Bot shuru howar somoy ekti time mark kore rakhbo
    if "last_timestamp" not in rr_state:
        # Initial timestamp is now, in seconds
        rr_state["last_timestamp"] = time.time()
        save_rr_state(rr_state)
        print(f"[RUN] Initialized time marker: {rr_state['last_timestamp']}")
    # -------------------------------------------------------------------------

    if not config.BOT_TOKENS:
        print("[ERR] No BOT_TOKENS configured in config.py. Exiting.")
        return

    num_bots = len(config.BOT_TOKENS)
    if not config.BOT_CHAT_IDS:
        bot_chat_ids = [config.CHAT_ID] * num_bots
    else:
        bot_chat_ids = (config.BOT_CHAT_IDS + [config.BOT_CHAT_IDS[-1]] * num_bots)[:num_bots]

    try:
        while True:
            # 1. Fetch New Messages
            items = fetch_all_items()
            if isinstance(items, list):
                # sort by id ascending (oldest first)
                items_sorted = sorted(items, key=lambda x: x.get("id", 0))

                for it in items_sorted:
                    iid = it.get("id")
                    if iid is None: continue
                    
                    # --- NEW LOGIC: Skip old items based on time ---
                    # it.get("time") API theke ashche kina check korun
                    # jodi API theke time na ashe, tobe id based logic a fire jete hobe
                    item_time = it.get("timestamp") # <--- URL a timestamp thakle ekhane likhun
                    if item_time and item_time <= rr_state["last_timestamp"]:
                        continue # Time purono hole skip koro
                    # -------------------------------------------------

                    # check if already sent (item_id check korbo)
                    is_already_sent = False
                    for data in sent_items.values():
                        if isinstance(data, dict) and str(data.get("item_id")) == str(iid):
                            is_already_sent = True
                            break
                    
                    if is_already_sent: continue

                    # choose bot
                    bot_idx = choose_next_bot(rr_state, num_bots)
                    token = config.BOT_TOKENS[bot_idx]
                    chat_id = bot_chat_ids[bot_idx] if bot_chat_ids[bot_idx] else config.CHAT_ID

                    text = format_item(it)
                    reply_markup = get_buttons(it) 
                    
                    # Message send kore id pawya
                    message_id = send_with_bot(token, chat_id, text, reply_markup)
                    
                    if message_id:
                        # Message data store kora (timestamp shoho)
                        sent_items[str(message_id)] = {
                            "timestamp": time.time(),
                            "token": token,
                            "chat_id": chat_id,
                            "item_id": str(iid)
                        }
                        save_sent_messages(sent_items)
                        print(f"[RUN] Sent message {message_id} (item={iid}) via bot#{bot_idx}")
                    else:
                        print(f"[RUN] failed to send id={iid} via bot#{bot_idx}")

            # 2. Message Delete Check (60 seconds)
            current_time = time.time()
            items_to_keep = {}
            for msg_id, data in sent_items.items():
                if isinstance(data, dict) and "timestamp" in data:
                    if current_time - data["timestamp"] > 60:
                        ok = delete_message_with_bot(data["token"], data["chat_id"], msg_id)
                        if not ok:
                            items_to_keep[msg_id] = data
                    else:
                        items_to_keep[msg_id] = data
                else:
                    items_to_keep[msg_id] = data
            
            if len(items_to_keep) != len(sent_items):
                sent_items = items_to_keep
                save_sent_messages(sent_items)

            # 3. SHORT SLEEP
            time.sleep(1)

    except KeyboardInterrupt:
        print("[RUN] stopped by user")
    finally:
        save_sent_messages(sent_items)
        save_rr_state(rr_state)

if __name__ == "__main__":
    run_loop()
