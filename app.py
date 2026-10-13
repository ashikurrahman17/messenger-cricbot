import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
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
        matches_list = data.get("typeMatches", [])
        
        msg_lower = user_msg.lower()
        is_general_query = msg_lower in ["score", "live", "cricbuzz", "cricket"]
        
        # সমস্ত ইন্টারন্যাশনাল, লিগ এবং উইমেনস ম্যাচগুলো এক জায়গায় করা হচ্ছে
        all_matches = []
        for t in matches_list:
            if t.get("matchType") in ["International", "League", "Women", "Domestic"]:
                for series in t.get("seriesMatches", []):
                    m_list = series.get("seriesAdWrapper", {}).get("matches", [])
                    if not m_list:
                        m_list = series.get("matches", [])
                    for m in m_list:
                        if "matchInfo" in m:
                            all_matches.append(m)

        if not all_matches:
            return "এই মুহূর্তে কোনো লাইভ ম্যাচ চলছে না।"

        if is_general_query:
            # জেনারেল 'score' লিখলে টপ ৩-৪টি ম্যাচের লিস্ট ও স্ট্যাটাস দেখাবে
            reply = "🏏 Live Cricket Matches:\n\n"
            count = 0
            for m in all_matches:
                info = m.get("matchInfo", {})
                team1 = info.get("team1", {}).get("teamName", "")
                team2 = info.get("team2", {}).get("teamName", "")
                status = info.get("status", "")
                
                reply += f"🔹 {team1} vs {team2}\n"
                reply += f"📌 {status}\n\n"
                
                count += 1
                if count >= 3:
                    break
            
            reply += "ব্যাটসম্যান ও বোলারের ডিটেইলস জানতে টিমের নাম (যেমন: ban) লিখে মেসেজ করুন।"
            return reply.strip()
        
        else:
            # স্পেসিফিক টিমের নাম দিয়ে খুঁজলে (যেমন: bd, ban, aus)
            search_terms = msg_lower.replace("vs", " ").split()
            
            # ইউজার 'bd' লিখলে যেন 'ban' বা 'bangladesh' খুঁজে পায়, তার জন্য স্মার্ট অ্যালিয়াস
            aliases = {
                "bd": ["ban", "bangladesh"],
                "ban": ["bd", "bangladesh"],
                "ind": ["india"],
                "pak": ["pakistan"],
                "sa": ["rsa", "south africa"],
                "rsa": ["sa", "south africa"],
                "nz": ["new zealand"],
                "eng": ["england"],
                "aus": ["australia"],
                "afg": ["afghanistan"],
                "sl": ["sri lanka", "sri"]
            }
            
            expanded_terms = set(search_terms)
            for term in search_terms:
                if term in aliases:
                    expanded_terms.update(aliases[term])
            
            target_match_id = None
            target_match_name = ""
            target_match_status = ""
            
            for m in all_matches:
                info = m.get("matchInfo", {})
                t1_s = info.get("team1", {}).get("teamSName", "").lower()
                t2_s = info.get("team2", {}).get("teamSName", "").lower()
                t1_n = info.get("team1", {}).get("teamName", "").lower()
                t2_n = info.get("team2", {}).get("teamName", "").lower()
                
                match_found = False
                for term in expanded_terms:
                    if term == t1_s or term == t2_s or term in t1_n or term in t2_n:
                        match_found = True
                        break
                        
                if match_found:
                    target_match_id = info.get("matchId")
                    target_match_name = f"{info.get('team1', {}).get('teamName')} vs {info.get('team2', {}).get('teamName')}"
                    target_match_status = info.get("status", "")
                    
                    # যদি ম্যাচটি ইন-প্রগ্রেস হয়, তবে সাথে সাথেই খোঁজা বন্ধ করে দেবে। 
                    # আর শেষ হয়ে গেলে অন্য লাইভ ম্যাচ আছে কিনা চেক করবে।
                    if info.get("state") == "In Progress":
                        break
                        
            if not target_match_id:
                return "আপনার কাঙ্ক্ষিত ম্যাচটি এখন চলছে না বা লিস্টে নেই।"

            # matchId দিয়ে ব্যাটার ও বোলারের বিস্তারিত লাইভ স্কোর আনা
            url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
            score_resp = requests.get(url_live_score, headers=headers, timeout=10)
            
            if score_resp.status_code != 200:
                # কোনো কারণে লাইভ স্কোর ফেচ না হলে আগের বেসিক স্ট্যাটাস দিয়ে দেবে
                return f"🏏 {target_match_name}\n📌 {target_match_status}\n\n(বিস্তারিত ডেটা এখন পাওয়া যাচ্ছে না)"
                
            score_data = score_resp.json()
            miniscore = score_data.get("miniscore", {})
            
            # ম্যাচ শেষ হয়ে গেলে বা customStatus না থাকলে আসল স্ট্যাটাস দেখাবে
            match_status = miniscore.get("matchScoreDetails", {}).get("customStatus") or target_match_status
            
            reply = f"🏏 {target_match_name}\n📌 Status: {match_status}\n\n"
            
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
                
            # পার্টনারশিপ এবং লাস্ট কয়েক বল
            partnership = miniscore.get('partnerShip')
            if partnership:
                reply += f"\n🤝 Partnership: {partnership}"
                
            recent = miniscore.get("recentOvsStats")
            if recent:
                reply += f"\n📊 Recent: {recent}"
                
            return reply.strip()

    except Exception as e:
        print(f"API Error: {e}")
        return "সার্ভারে সমস্যা, একটু পর চেষ্টা করুন।"

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
                    
                    keywords = ["score", "live", "cricbuzz", "cricket", "ban", "afg", "bd", "sa", "aus", "ind", "eng", "pak", "nz", "vs"]
                    
                    if any(keyword in message_text.lower() for keyword in keywords):
                        live_score_reply = get_detailed_live_score(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "Live score জানতে 'score' অথবা নির্দিষ্ট দলের নাম (যেমন: bd, ind) লিখে মেসেজ করুন।")
                        
        return "EVENT_RECEIVED", 200
    
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
