import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "84979f4188mshaf1d97ff6398457p1d4d3djsn974c4fcce480")  # Default key if not set in .env

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

    t1_score = match_score.get("team1Score") or {}
    t2_score = match_score.get("team2Score") or {}
    
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

def handle_cricket_query(user_msg):
    msg_lower = user_msg.lower().strip()
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com"
    }
    
    # প্রথমে সব ম্যাচের বেসিক লিস্ট আনছি (যাতে নাম ও মেইন স্কোর গ্যারান্টিড পাওয়া যায়)
    url_live_matches = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    try:
        response = requests.get(url_live_matches, headers=headers, timeout=10)
        if response.status_code != 200:
            return "এ মুহূর্তে স্কোর পাওয়া যাচ্ছে না।"
            
        matches_list = response.json().get("typeMatches") or []
        all_matches = []
        
        for t in matches_list:
            if t.get("matchType") in ["International", "League", "Women", "Domestic"]:
                for series in t.get("seriesMatches") or []:
                    wrapper_matches = series.get("seriesAdWrapper", {}).get("matches") or series.get("matches") or []
                    for m in wrapper_matches:
                        if "matchInfo" in m:
                            all_matches.append(m)

        if not all_matches:
            return "এই মুহূর্তে কোনো লাইভ ম্যাচ চলছে না।"

        is_general_query = msg_lower in ["score", "live", "cricbuzz", "cricket"]
        is_id_query = msg_lower.isdigit()
        
        # ১. যদি 'score' বা 'live' লিখে
        if is_general_query:
            reply = "🏆 Live Cricket Updates:\n\n"
            count = 0
            for m in all_matches:
                info = m.get("matchInfo") or {}
                t1_n = info.get("team1", {}).get("teamName", "")
                t2_n = info.get("team2", {}).get("teamName", "")
                t1_s = info.get("team1", {}).get("teamSName", "")
                t2_s = info.get("team2", {}).get("teamSName", "")
                status = info.get("status", "")
                match_id = info.get("matchId")
                
                reply += f"🔹 {t1_n} vs {t2_n}\n"
                score_str = get_score_str(m.get("matchScore"), t1_s, t2_s)
                if score_str:
                    reply += score_str
                reply += f"📌 {status}\n"
                reply += f"🔑 Details dekhte likhun: {match_id}\n\n"
                
                count += 1
                if count >= 3:
                    break
            return reply.strip()

        # ২. যদি আইডি বা নির্দিষ্ট দলের নাম লিখে
        target_match = None
        
        if is_id_query:
            for m in all_matches:
                if str(m.get("matchInfo", {}).get("matchId")) == msg_lower:
                    target_match = m
                    break
        else:
            aliases = {"bd": ["ban", "bangladesh"], "ban": ["bd", "bangladesh"], "ind": ["india"], "sa": ["rsa", "south africa"]}
            search_terms = msg_lower.replace("vs", " ").split()
            expanded_terms = set(search_terms)
            for term in search_terms:
                if term in aliases: expanded_terms.update(aliases[term])
            
            for m in all_matches:
                info = m.get("matchInfo") or {}
                t1_n = info.get("team1", {}).get("teamName", "").lower()
                t2_n = info.get("team2", {}).get("teamName", "").lower()
                t1_s = info.get("team1", {}).get("teamSName", "").lower()
                t2_s = info.get("team2", {}).get("teamSName", "").lower()
                
                match_found = any(term in [t1_s, t2_s, t1_n, t2_n] for term in expanded_terms)
                if match_found:
                    target_match = m
                    if info.get("state") == "In Progress":
                        break
                        
        if not target_match:
            return "আপনার কাঙ্ক্ষিত ম্যাচটি এখন চলছে না বা লিস্টে নেই।"

        # ম্যাচ পাওয়া গেছে! এবার মেইন স্কোর ও নামগুলো বের করে নিই
        info = target_match.get("matchInfo") or {}
        t1_name = info.get("team1", {}).get("teamName", "Team 1")
        t2_name = info.get("team2", {}).get("teamName", "Team 2")
        t1_sname = info.get("team1", {}).get("teamSName", "")
        t2_sname = info.get("team2", {}).get("teamSName", "")
        target_match_id = info.get("matchId")
        base_status = info.get("status", "")
        
        reply = f"🏆 {t1_name} vs {t2_name}\n\n"
        
        main_score_str = get_score_str(target_match.get("matchScore"), t1_sname, t2_sname)
        if main_score_str:
            reply += main_score_str
            reply += "\n"

        # ৩. এবার আইডি দিয়ে ব্যাটার-বোলারের ডিটেইলস আনা
        url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
        score_resp = requests.get(url_live_score, headers=headers, timeout=10)
        
        if score_resp.status_code == 200:
            score_data = score_resp.json()
            miniscore = score_data.get("miniscore") or score_data.get("miniScore") or {}
            
            match_details = miniscore.get("matchScoreDetails") or miniscore.get("matchscoredetails") or {}
            match_status = match_details.get("customStatus") or match_details.get("customstatus") or base_status
            reply += f"📌 Status: {match_status}\n\n"
            
            # ব্যাটার
            striker = miniscore.get("batsmanStriker") or miniscore.get("batsmanstriker") or miniscore.get("striker") or {}
            non_striker = miniscore.get("batsmanNonStriker") or miniscore.get("batsmannonstriker") or miniscore.get("nonStriker") or {}
            
            if striker or non_striker:
                reply += "🏏 Batting:\n"
                if striker:
                    s_name = striker.get("batName") or striker.get("batname") or striker.get("name") or "Batsman"
                    s_runs = striker.get("batRuns") or striker.get("runs") or "0"
                    s_balls = striker.get("batBalls") or striker.get("balls") or "0"
                    reply += f"👉 {s_name}*: {s_runs} ({s_balls})\n"
                if non_striker:
                    ns_name = non_striker.get("batName") or non_striker.get("batname") or non_striker.get("name") or "Batsman"
                    ns_runs = non_striker.get("batRuns") or non_striker.get("runs") or "0"
                    ns_balls = non_striker.get("batBalls") or non_striker.get("balls") or "0"
                    reply += f"   {ns_name}: {ns_runs} ({ns_balls})\n"
                reply += "\n"
                
            # বোলার
            bowler = miniscore.get("bowlerStriker") or miniscore.get("bowlerstriker") or miniscore.get("bowler") or {}
            if bowler:
                b_name = bowler.get("bowlName") or bowler.get("bowlname") or bowler.get("name") or "Bowler"
                b_wkts = bowler.get("bowlWkts") or bowler.get("wickets") or bowler.get("wkts") or "0"
                b_runs = bowler.get("bowlRuns") or bowler.get("runs") or "0"
                b_ovs = bowler.get("bowlOvs") or bowler.get("overs") or "0"
                reply += "⚾ Bowling:\n"
                reply += f"👉 {b_name}: {b_wkts}/{b_runs} ({b_ovs} ov)\n\n"
                
            # পার্টনারশিপ
            partnership = miniscore.get("partnerShip") or miniscore.get("partnership")
            if partnership:
                reply += f"🤝 Partnership: {partnership}\n"
                
            # রিসেন্ট বল
            recent = miniscore.get("recentOvsStats") or miniscore.get("recentovsstats")
            if recent:
                reply += f"📉 Recent: {recent}"
        else:
            reply += f"📌 Status: {base_status}"
            
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
    return "Cricket Bot is running smoothly with Unified Logic!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
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
                    
                    if any(keyword in message_text.lower() for keyword in keywords) or message_text.isdigit():
                        live_score_reply = handle_cricket_query(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "Live score জানতে 'score' লিখুন অথবা Match ID দিন।")
                        
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
