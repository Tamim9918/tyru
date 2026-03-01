import requests
import telebot
from datetime import datetime
import time
import re
# ==========================
# CONFIG
# ==========================
BOT_TOKEN = "8630811530:AAGxCDDqV0fLbeLcVb0eze1p6zGygfr1bqA"
USERNAME = "sss148900"
PASSWORD = "sss148900"

BASE = "http://51.89.99.105/NumberPanel"

bot = telebot.TeleBot(BOT_TOKEN)
session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0"
}

headers_ajax = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}


# ==========================
# LOGIN FUNCTION
# ==========================
def login():
    try:
        print("Opening login page...")
        r = session.get(BASE + "/login", headers=headers)

        html = r.text

        # Extract captcha numbers dynamically
        match = re.search(r'What is (\d+) \+ (\d+)', html)

        if not match:
            print("Captcha not found!")
            return False

        num1 = int(match.group(1))
        num2 = int(match.group(2))
        captcha_answer = str(num1 + num2)

        print(f"Captcha: {num1} + {num2} = {captcha_answer}")

        payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "capt": captcha_answer
        }

        headers_post = {
            "User-Agent": "Mozilla/5.0",
            "Referer": BASE + "/login",
            "Origin": "http://51.89.99.105",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        print("Sending login request...")
        r2 = session.post(BASE + "/signin", data=payload, headers=headers_post)

        print("Signin status:", r2.status_code)

        # Check redirect
        if "Location" in r2.headers:
            print("Redirected to:", r2.headers["Location"])

        dash = session.get(BASE + "/client/SMSDashboard", headers=headers)

        if "SMSDashboard" in dash.text or "Logout" in dash.text:
            print("Login SUCCESS")
            return True

        print("Login FAILED")
        return False

    except Exception as e:
        print("Login Error:", e)
        return False


# ==========================
# FETCH SMS
# ==========================

def fetch_sms():
    try:
        print("Opening SMSCDRStats page...")
        stats = session.get(BASE + "/client/SMSCDRStats", headers=headers)

        html = stats.text

        # Extract sesskey from this page
        match = re.search(r'sesskey=([A-Za-z0-9+/=]+)', html)

        if not match:
            print("Sesskey NOT found in SMSCDRStats page!")
            print(html[:1200])
            return None

        sesskey = match.group(1)
        print("Dynamic Sesskey:", sesskey)

        today = datetime.now().strftime("%Y-%m-%d")

        url = BASE + "/client/res/data_smscdr.php"

        params = {
            "fdate1": f"{today} 00:00:00",
            "fdate2": f"{today} 23:59:59",
            "fg": "0",
            "sesskey": sesskey,
            "sEcho": "1",
            "iColumns": "7",
            "iDisplayStart": "0",
            "iDisplayLength": "-1"
        }

        r = session.get(url, params=params, headers=headers_ajax)

        print("SMS Status:", r.status_code)

        try:
            return r.json()
        except:
            print("Not JSON Response:")
            print(r.text[:500])
            return None

    except Exception as e:
        print("Fetch Error:", e)
        return None


# ==========================
# AUTO START SYSTEM (Updated)
# ==========================

def run_bot():
    print("Bot Starting and Monitoring SMS...")
    
    # প্রথমবার রান করার সময় একবার লগইন করে নেওয়া
    if not login():
        print("Initial login failed! Checking again in 60s...")
        time.sleep(60)

    while True:
        try:
            # ১. ডাটা ফেচ করার চেষ্টা করো
            data = fetch_sms()
            
            # ২. যদি সেশন আউট হয়ে যায় বা ডাটা না আসে
            if data is None:
                print("Session expired or error. Re-logging in...")
                if login():
                    continue 
                else:
                    print("Login failed. Sleeping for 1 minute before retry.")
                    time.sleep(60)
                    continue

            # ৩. ডাটা প্রসেস করো
            records = data.get("aaData", [])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Total SMS found: {len(records)}")
            
            # এখানে তুমি তোমার SMS প্রিন্ট বা টেলিগ্রামে পাঠানোর কাজ করতে পারো
            for row in records[:5]: # উদাহরণস্বরূপ প্রথম ৫টি
                print(f"Number: {row[1]} | Msg: {row[3]}")

        except Exception as e:
            print(f"Loop Error: {e}")
        
        # ৪. পরবর্তী চেকের জন্য অপেক্ষা
        print("Waiting 60 seconds for next check...")
        time.sleep(60)

# মেন পার্ট
if __name__ == "__main__":
    # যেহেতু তুমি ২৪/৭ অটো চেক করতে চাও, তাই সরাসরি run_bot() কল করা হলো
    run_bot()
