import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

# এই লাইনটি Gunicorn-এর জন্য অত্যাবশ্যক। এটি ছাড়া Render-এ ডিপ্লয় হবে না।
app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
# নিচে "YOUR_RAPIDAPI_KEY" এর জায়গায় আপনার RapidAPI থেকে পাওয়া আসল Key টি বসিয়ে দিন
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "84979f4188mshaf1d97ff6398457p1d4d3djsn974c4fcce480") 

def get_detailed_live_score(user_msg):
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com"
    }
    
    url_live_matches = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    
    try:
        response = requests.get(url_live_matches, headers=headers, timeout=10)
        if response.status_code != 200:
            return "এ মুহূর্তে স্কোর পাওয়া যাচ্ছে না, একটু পর চেষ্টা করুন।"
            
        data = response.json()
        matches = data.get("typeMatches", [])
        
        target_match_id = None
        target_match_name = ""
        
        msg_lower = user_msg.lower()
        is_general_query = msg_lower in ["score", "live", "cricbuzz", "cricket"]
        
        # ধাপ ১: ম্যাচ লিস্ট থেকে সঠিক ম্যাচের ID খুঁজে বের করা
        for t in matches:
            if t.get("matchType") == "International":
                for series in t.get("seriesMatches", []):
                    m_list = series.get("seriesAdWrapper", {}).get("matches", [])
                    if not m_list:
                        m_list = series.get("matches", [])
                        
                    for m in m_list:
                        info = m.get("matchInfo", {})
                        team1_s = info.get("team1", {}).get("teamSName", "").lower()
                        team2_s = info.get("team2", {}).get("teamSName", "").lower()
                        team1_f = info.get("team1", {}).get("teamName", "").lower()
                        team2_f = info.get("team2", {}).get("teamName", "").lower()
                        
                        if is_general_query:
                            target_match_id = info.get("matchId")
                            target_match_name = f"{info.get('team1', {}).get('teamName')} vs {info.get('team2', {}).get('teamName')}"
                            break
                        else:
                            search_terms = msg_lower.replace("vs", " ").split()
                            # যদি ইউজার নির্দিষ্ট টিমের নাম দিয়ে সার্চ করে
                            if any(word in team1_s or word in team2_s or word in team1_f or word in team2_f for word in search_terms):
                                target_match_id = info.get("matchId")
                                target_match_name = f"{info.get('team1', {}).get('teamName')} vs {info.get('team2', {}).get('teamName')}"
                                break
                    if target_match_id:
                        break
            if target_match_id:
                break
                
        if not target_match_id:
            return "আপনার কাঙ্ক্ষিত ইন্টারন্যাশনাল ম্যাচটি এখন চলছে না বা শেষ হয়ে গেছে।"
            
        # ধাপ ২: matchId দিয়ে ব্যাটার ও বোলারের বিস্তারিত লাইভ স্কোর আনা
        url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
        
        score_resp = requests.get(url_live_score, headers=headers, timeout=10)
        if score_resp.status_code != 200:
            return "ম্যাচের বিস্তারিত তথ্য এই মুহূর্তে পাওয়া যাচ্ছে না।"
            
        score_data = score_resp.json()
        miniscore = score_data.get("miniscore", {})
        match_status = miniscore.get("matchScoreDetails", {}).get("customStatus", "Match in progress")
        
        reply = f"🏏 {target_match_name}\n"
        reply += f"📌 Status: {match_status}\n\n"
        
        # ব্যাটারদের তথ্য
        striker = miniscore.get("striker", {})
        non_striker = miniscore.get("nonStriker", {})
        
        if striker or non_striker:
            reply += "🏏 Batting:\n"
            if striker:
                reply += f"👉 {striker.get('batName')}*: {striker.get('batRuns')} ({striker.get('batBalls')})\n"
            if non_striker:
                reply += f"   {non_striker.get('batName')}: {non_striker.get('batRuns')} ({non_striker.get('batBalls')})\n\n"
            
        # বোলারদের তথ্য
        bowler = miniscore.get("bowler", {})
        if bowler:
            reply += "⚾ Bowling:\n"
            reply += f"👉 {bowler.get('bowlName')}: {bowler.get('bowlWkts')}/{bowler.get('bowlRuns')} ({bowler.get('bowlOvs')} ov)\n"
            
        # পার্টনারশিপ
        partnership = miniscore.get('partnerShip')
        if partnership:
            reply += f"\n🤝 Partnership: {partnership}"
        
        return reply.strip()

    except Exception as e:
        print(f"API Error: {e}")
        return "সার্ভারে সমস্যা, একটু পর চেষ্টা করুন।"

def send_message(recipient_id, message_text):
    """
    Meta Graph API v19.0 দিয়ে মেসেজ সেন্ড করা
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
    return "Cricket Bot is running perfectly with RapidAPI!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification token mismatch", 403
    return "Webhook is ready", 200

@app.route("/webhook", methods=["POST"])
def webhook_events():
    data = request.get_json()
    
    if data and data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"]["text"].strip()
                    
                    keywords = ["score", "live", "cricbuzz", "cricket", "ban", "afg", "bd", "sa", "aus", "ind", "eng", "vs"]
                    
                    if any(keyword in message_text.lower() for keyword in keywords):
                        live_score_reply = get_detailed_live_score(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "Live score জানতে 'score', 'live' বা টিমের নাম (যেমন: ban) লিখে মেসেজ করুন।")
                        
        return "EVENT_RECEIVED", 200
    
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)