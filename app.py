import os
import requests
from flask import Flask, request
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env ফাইল থেকে ভ্যারিয়েবল লোড করা হচ্ছে
load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

def get_live_score():
    """
    Cricbuzz এর মোবাইল সাইট থেকে লাইভ স্কোর স্ক্র্যাপ করার ফাংশন।
    """
    url = "https://m.cricbuzz.com/cricket-match/live-scores"
    # মোবাইল সাইট থেকে ডেটা আনার জন্য User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # মোবাইল সাইটের লেআউট অনুযায়ী প্রথম লাইভ ম্যাচের ব্লক খোঁজা
        # (বি.দ্র: ক্রিকবাজ তাদের ক্লাসের নাম পরিবর্তন করলে এই অংশটি আপডেট করতে হতে পারে)
        match_block = soup.find('div', class_='cb-lv-scrs-col') 
        
        if match_block:
            # টিমের নাম ও স্কোর এক্সট্রাক্ট করা
            score_text = match_block.get_text(separator="\n").strip()
            # অপ্রয়োজনীয় স্পেস বাদ দিয়ে সুন্দর ফরম্যাটে সাজানো
            lines = [line.strip() for line in score_text.split('\n') if line.strip()]
            
            # আপনি চাইলে এখানে রেজেক্স (regex) দিয়ে আরও কাস্টমাইজ করতে পারেন
            # আপাতত স্ক্র্যাপ করা ডেটা সুন্দরভাবে জোড়া লাগিয়ে পাঠানো হচ্ছে
            formatted_score = "\n".join(lines)
            return f"🏏 লাইভ আপডেট:\n\n{formatted_score}"
        else:
            return "Score ekhon pawa jacche na, 2 min por try korun"
            
    except Exception as e:
        # কোনো এরর হলে বা ক্রিকবাজ ব্লক করলে এই মেসেজ যাবে
        print(f"Scraping Error: {e}")
        return "Score ekhon pawa jacche na, 2 min por try korun"

def send_message(recipient_id, message_text):
    """
    Meta Graph API (v19.0) ব্যবহার করে ইউজারকে মেসেজ পাঠানোর ফাংশন।
    """
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")

@app.route("/", methods=["GET"])
def index():
    return "Cricket Bot is running!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Meta Developer কনসোল থেকে ওয়েবহুক ভেরিফাই করার জন্য GET রিকোয়েস্ট হ্যান্ডেল করে।
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Verification token mismatch", 403
    return "Hello World", 200

@app.route("/webhook", methods=["POST"])
def webhook_events():
    """
    ইউজারের পাঠানো মেসেজ রিসিভ এবং প্রসেস করার জন্য POST রিকোয়েস্ট হ্যান্ডেল করে।
    """
    data = request.get_json()
    
    if data and data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                # যদি এটি কোনো সাধারণ টেক্সট মেসেজ হয়
                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]["text"].lower()
                    
                    # ট্রিগার কিওয়ার্ড চেক করা
                    keywords = ["score", "live", "cricbuzz", "ban vs afg", "sa vs aus"]
                    
                    if any(keyword in message_text for keyword in keywords):
                        # লাইভ স্কোর স্ক্র্যাপ করে ইউজারের কাছে পাঠানো
                        live_score_reply = get_live_score()
                        send_message(sender_id, live_score_reply)
                    else:
                        # অন্য কোনো মেসেজ দিলে ডিফল্ট রিপ্লাই
                        send_message(sender_id, "লাইভ স্কোর জানতে 'score', 'live' বা টিমের নাম লিখে মেসেজ করুন।")
                        
        return "EVENT_RECEIVED", 200
    
    return "Not Found", 404

if __name__ == "__main__":
    # Render এ পোর্ট ডাইনামিক্যালি অ্যাসাইন হয়, তাই os.environ.get ব্যবহার করা হয়েছে
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)