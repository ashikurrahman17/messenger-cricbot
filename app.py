import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
# আপনার CricAPI Key এখানে .env থেকে লোড করতে পারেন অথবা সরাসরি বসাতে পারেন
CRIC_API_KEY = os.getenv("CRIC_API_KEY", "c0809dcb-7afd-41f0-9c04-1c3083f7bb69") # YOUR_API_KEY_HERE এর জায়গায় আপনার আসল কী বসান

def get_live_score(user_msg):
    url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}&offset=0"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return "এ মুহূর্তে সার্ভার থেকে ডেটা পাওয়া যাচ্ছে না। কিছুক্ষণ পর চেষ্টা করুন।"
            
        data = response.json()
        matches = data.get("data", [])
        
        if not matches:
            return "এ মুহূর্তে কোনো লাইভ ম্যাচ চলছে না।"
            
        msg_lower = user_msg.lower()
        is_general_query = msg_lower in ["score", "live", "cricbuzz"]
        
        reply = "🏏 লাইভ ক্রিকেট আপডেট:\n\n"
        match_found = 0
        
        for match in matches:
            name = match.get('name', '')
            status = match.get('status', '')
            
            # স্পেসিফিক ম্যাচ ফিল্টার (যেমন "BAN", "SA")
            if not is_general_query:
                search_keywords = msg_lower.replace("vs", " ").split()
                if not any(word in name.lower() for word in search_keywords):
                    continue
            
            reply += f"🔹 {name}\n"
            reply += f"📌 {status}\n"
            
            scores = match.get("score", [])
            if scores:
                for sc in scores:
                    team = sc.get('inning', '').replace('Inning', 'Inn')
                    runs = sc.get('r', 0)
                    wkts = sc.get('w', 0)
                    overs = sc.get('o', 0)
                    reply += f"   - {team}: {runs}/{wkts} ({overs} ov)\n"
            else:
                reply += "   - স্কোর এখনো আপডেট হয়নি।\n"
            
            reply += "\n"
            match_found += 1
            
            if is_general_query and match_found >= 3:
                break
                
        if match_found == 0:
            return "আপনার কাঙ্ক্ষিত ম্যাচটি পাওয়া যায়নি। দয়া করে 'score' লিখে বর্তমান ম্যাচগুলোর তালিকা দেখুন।"
            
        return reply.strip()

    except Exception as e:
        print(f"API Error: {e}")
        return "স্কোর আনতে সমস্যা হচ্ছে, ২ মিনিট পর আবার চেষ্টা করুন।"

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    requests.post(url, headers=headers, json=payload)

@app.route("/", methods=["GET"])
def index():
    return "Cricket Bot is running!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification token mismatch", 403

@app.route("/webhook", methods=["POST"])
def webhook_events():
    data = request.get_json()
    if data and data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]["text"].strip()
                    
                    keywords = ["score", "live", "cricbuzz", "ban", "afg", "sa", "aus", "vs"]
                    if any(keyword in message_text.lower() for keyword in keywords):
                        live_score_reply = get_live_score(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "লাইভ স্কোর জানতে 'score', 'live' বা টিমের নাম লিখে মেসেজ করুন।")
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)