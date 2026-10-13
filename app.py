import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "84979f4188mshaf1d97ff6398457p1d4d3djsn974c4fcce480") 

# স্কোর সুন্দরভাবে সাজানোর জন্য হেল্পার ফাংশন
def get_score_str(match_score, team1_name, team2_name):
    if not match_score:
        return ""
    
    def format_innings(inngs):
        if not inngs: return ""
        r = inngs.get('runs', 0)
        w = inngs.get('wickets', 0)
        o = inngs.get('overs', 0)
        decl = "d" if inngs.get('isDeclared') else ""
        return f"{r}/{w}{decl} ({o} ov)"

    t1_score = match_score.get("team1Score", {})
    t2_score = match_score.get("team2Score", {})
    
    t1_i1 = format_innings(t1_score.get("inngs1"))
    t1_i2 = format_innings(t1_score.get("inngs2"))
    t2_i1 = format_innings(t2_score.get("inngs1"))
    t2_i2 = format_innings(t2_score.get("inngs2"))
    
    t1_final = t1_i1 + (f" & {t1_i2}" if t1_i2 else "")
    t2_final = t2_i1 + (f" & {t2_i2}" if t2_i2 else "")
    
    res = ""
    if t1_final: res += f"🏏 {team1_name}: {t1_final}\n"
    if t2_final: res += f"🏏 {team2_name}: {t2_final}\n"
    
    return res

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
            reply = "🏆 Live Cricket Updates:\n\n"
            count = 0
            for m in all_matches:
                info = m.get("matchInfo", {})
                team1 = info.get("team1", {}).get("teamSName", "")
                team2 = info.get("team2", {}).get("teamSName", "")
                status = info.get("status", "")
                
                reply += f"🔹 {team1} vs {team2}\n"
                
                # মূল স্কোর বসানো হচ্ছে
                score_str = get_score_str(m.get("matchScore"), team1, team2)
                if score_str:
                    reply += score_str
                    
                reply += f"📌 {status}\n\n"
                
                count += 1
                if count >= 3:
                    break
            
            reply += "বিস্তারিত জানতে টিমের নাম (যেমন: ban) লিখে মেসেজ করুন।"
            return reply.strip()
        
        else:
            search_terms = msg_lower.replace("vs", " ").split()
            aliases = {
                "bd": ["ban", "bangladesh"], "ban": ["bd", "bangladesh"],
                "ind": ["india"], "pak": ["pakistan"],
                "sa": ["rsa", "south africa"], "rsa": ["sa", "south africa"],
                "nz": ["new zealand"], "eng": ["england"],
                "aus": ["australia"], "afg": ["afghanistan"], "sl": ["sri lanka", "sri"]
            }
            
            expanded_terms = set(search_terms)
            for term in search_terms:
                if term in aliases:
                    expanded_terms.update(aliases[term])
            
            target_match_id = None
            target_match_name = ""
            target_match_status = ""
            target_match_score = {}
            t1_sname = ""
            t2_sname = ""
            
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
                    target_match_score = m.get("matchScore", {})
                    t1_sname = info.get("team1", {}).get("teamSName", "")
                    t2_sname = info.get("team2", {}).get("teamSName", "")
                    
                    if info.get("state") == "In Progress":
                        break
                        
            if not target_match_id:
                return "আপনার কাঙ্ক্ষিত ম্যাচটি এখন চলছে না বা লিস্টে নেই।"

            reply = f"🏆 {target_match_name}\n\n"
            
            # ১০০% গ্যারান্টিড মেইন স্কোর
            main_score_str = get_score_str(target_match_score, t1_sname, t2_sname)
            if main_score_str:
                reply += main_score_str
                reply += "\n"

            # লাইভ স্কোরের বিস্তারিত আনার চেষ্টা
            url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
            score_resp = requests.get(url_live_score, headers=headers, timeout=10)
            
            if score_resp.status_code == 200:
                score_data = score_resp.json()
                miniscore = score_data.get("miniscore") or {}
                
                match_status = miniscore.get("matchScoreDetails", {}).get("customStatus") or target_match_status
                reply += f"📌 Status: {match_status}\n\n"
                
                striker = miniscore.get("batsmanStriker") or miniscore.get("striker") or {}
                non_striker = miniscore.get("batsmanNonStriker") or miniscore.get("nonStriker") or {}
                
                if striker or non_striker:
                    reply += "🏏 Batting:\n"
                    if striker:
                        reply += f"👉 {striker.get('batName')}*: {striker.get('batRuns')} ({striker.get('batBalls')})\n"
                    if non_striker:
                        reply += f"   {non_striker.get('batName')}: {non_striker.get('batRuns')} ({non_striker.get('batBalls')})\n\n"
                    
                bowler = miniscore.get("bowlerStriker") or miniscore.get("bowler") or {}
                if bowler:
                    reply += "⚾ Bowling:\n"
                    reply += f"👉 {bowler.get('bowlName')}: {bowler.get('bowlWkts')}/{bowler.get('bowlRuns')} ({bowler.get('bowlOvs')} ov)\n\n"
                    
                partnership = miniscore.get('partnerShip')
                if partnership:
                    reply += f"🤝 Partnership: {partnership}\n"
                    
                recent = miniscore.get("recentOvsStats")
                if recent:
                    reply += f"📉 Recent: {recent}"
            else:
                reply += f"📌 Status: {target_match_status}"
                
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
