import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "0435491e0emshf98c30b0b288a90p151f59jsn176e7964c638")  # Default API Key if not set in .env

aliases = {
    "bd": ["ban", "bangladesh"], "ban": ["bd", "bangladesh"], 
    "ind": ["india"], "sa": ["rsa", "south africa"], 
    "aus": ["australia"], "nz": ["new zealand"], 
    "eng": ["england"], "pak": ["pakistan"], 
    "sl": ["sri lanka", "srilanka"], "afg": ["afghanistan"], 
    "wi": ["west indies"], "zim": ["zimbabwe"]
}

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
    if t1_final: res += f"{team1_name}: {t1_final}  "
    if t2_final: res += f"{team2_name}: {t2_final}"
    return res.strip()

def extract_live_details(score_data, target_match_status="", main_score_str=""):
    miniscore = score_data.get("miniscore") or score_data.get("miniScore") or {}
    header = score_data.get("matchHeader") or score_data.get("matchheader") or {}
    
    match_details = miniscore.get("matchScoreDetails") or miniscore.get("matchscoredetails") or {}
    match_status = match_details.get("customStatus") or match_details.get("customstatus") or header.get("status") or target_match_status
    
    reply = f"📌 {match_status}\n\n"
    
    crr = miniscore.get("currentRunRate") or miniscore.get("crr") or ""
    if main_score_str:
        reply += f"📊 Score: {main_score_str}\n"
        if crr:
            reply += f"📈 CRR: {crr}\n"
        reply += "\n"
        
    striker = miniscore.get("batsmanStriker") or miniscore.get("batsmanstriker") or miniscore.get("striker") or {}
    non_striker = miniscore.get("batsmanNonStriker") or miniscore.get("batsmannonstriker") or miniscore.get("nonStriker") or {}
    
    if striker or non_striker:
        reply += "🏏 BATTERS:\n"
        if striker:
            s_name = striker.get("batName") or striker.get("batname") or striker.get("name") or "Batsman 1"
            s_r = str(striker.get("batRuns") or striker.get("runs") or "0")
            s_b = str(striker.get("batBalls") or striker.get("balls") or "0")
            s_4s = str(striker.get("batFours") or striker.get("fours") or "0")
            s_6s = str(striker.get("batSixes") or striker.get("sixes") or "0")
            s_sr = str(striker.get("batStrikeRate") or striker.get("strikerate") or "0.00")
            reply += f"👉 {s_name}* : {s_r} ({s_b}) | 4s:{s_4s} 6s:{s_6s} | SR:{s_sr}\n"
            
        if non_striker:
            ns_name = non_striker.get("batName") or non_striker.get("batname") or non_striker.get("name") or "Batsman 2"
            ns_r = str(non_striker.get("batRuns") or non_striker.get("runs") or "0")
            ns_b = str(non_striker.get("batBalls") or non_striker.get("balls") or "0")
            ns_4s = str(non_striker.get("batFours") or non_striker.get("fours") or "0")
            ns_6s = str(non_striker.get("batSixes") or non_striker.get("sixes") or "0")
            ns_sr = str(non_striker.get("batStrikeRate") or non_striker.get("strikerate") or "0.00")
            reply += f"   {ns_name} : {ns_r} ({ns_b}) | 4s:{ns_4s} 6s:{ns_6s} | SR:{ns_sr}\n"
        reply += "\n"
        
    bowler = miniscore.get("bowlerStriker") or miniscore.get("bowlerstriker") or miniscore.get("bowler") or {}
    bowler_ns = miniscore.get("bowlerNonStriker") or miniscore.get("bowlernonstriker") or {}
    
    if bowler or bowler_ns:
        reply += "⚾ BOWLERS:\n"
        if bowler:
            b_name = bowler.get("bowlName") or bowler.get("bowlname") or bowler.get("name") or "Bowler 1"
            b_o = str(bowler.get("bowlOvs") or bowler.get("overs") or "0")
            b_m = str(bowler.get("bowlMaidens") or bowler.get("maidens") or "0")
            b_r = str(bowler.get("bowlRuns") or bowler.get("runs") or "0")
            b_w = str(bowler.get("bowlWkts") or bowler.get("wickets") or bowler.get("wkts") or "0")
            b_eco = str(bowler.get("bowlEcon") or bowler.get("economy") or "0.00")
            reply += f"👉 {b_name}* : {b_o}-{b_m}-{b_r}-{b_w} | Eco:{b_eco}\n"
            
        if bowler_ns:
            bns_name = bowler_ns.get("bowlName") or bowler_ns.get("bowlname") or bowler_ns.get("name") or "Bowler 2"
            bns_o = str(bowler_ns.get("bowlOvs") or bowler_ns.get("overs") or "0")
            bns_m = str(bowler_ns.get("bowlMaidens") or bowler_ns.get("maidens") or "0")
            bns_r = str(bowler_ns.get("bowlRuns") or bowler_ns.get("runs") or "0")
            bns_w = str(bowler_ns.get("bowlWkts") or bowler_ns.get("wickets") or bowler_ns.get("wkts") or "0")
            bns_eco = str(bowler_ns.get("bowlEcon") or bowler_ns.get("economy") or "0.00")
            reply += f"   {bns_name} : {bns_o}-{bns_m}-{bns_r}-{bns_w} | Eco:{bns_eco}\n"
        reply += "\n"
        
    reply += "🔑 KEY STATS:\n"
    partnership = miniscore.get("partnerShip") or miniscore.get("partnership")
    if partnership:
        reply += f"🤝 Partnership: {partnership}\n"
        
    last_wkt = miniscore.get("lastWkt") or miniscore.get("lastwkt") or miniscore.get("lastWicket")
    if last_wkt:
        reply += f"🔻 Last Wkt: {last_wkt}\n"
        
    recent = miniscore.get("recentOvsStats") or miniscore.get("recentovsstats") or miniscore.get("curovsstats") or miniscore.get("curOvsStats")
    if recent:
        reply += f"📉 Recent: {recent}\n"
        
    return reply.strip()

def extract_full_scorecard(scard_data, base_status=""):
    scorecards = scard_data.get("scorecard") or []
    if not scorecards:
        return f"📌 {base_status}\n\n❌ Full scorecard not available yet."
        
    reply = f"📊 FULL MATCH SCORECARD\n📌 {base_status}\n{'='*30}\n\n"
    
    for inn in scorecards:
        inn_name = inn.get("inningsname", inn.get("batteam", f"Innings {inn.get('inningsid')}"))
        score = inn.get("score")
        wkts = inn.get("wickets")
        ovs = inn.get("overs")
        score_str = f"{score}/{wkts} ({ovs} ov)" if score is not None else ""
        
        reply += f"🏏 {inn_name}  {score_str}\n\n"
        
        reply += "BATTERS:\n"
        batsmen = inn.get("batsman") or []
        for b in batsmen:
            name = b.get("name", "")
            r = str(b.get("runs", "0"))
            balls = str(b.get("balls", "0"))
            out_desc = b.get("outdec", "")
            
            if out_desc and "Did not Bat" not in out_desc:
                reply += f"👉 {name}: {r} ({balls}) - {out_desc}\n"
                
        reply += "\nBOWLERS:\n"
        bowlers = inn.get("bowler") or []
        for b in bowlers:
            name = b.get("name", "")
            w = str(b.get("wickets", "0"))
            r = str(b.get("runs", "0"))
            o = str(b.get("overs", "0"))
            
            if name:
                reply += f"👉 {name}: {w}/{r} ({o} ov)\n"
        reply += f"\n{'-'*30}\n\n"
        
    return reply.strip()

def get_all_api_matches(headers):
    all_matches = []
    urls = [
        "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
        "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                type_matches = resp.json().get("typeMatches") or []
                for t in type_matches:
                    if t.get("matchType") in ["International", "League", "Women", "Domestic"]:
                        for series in t.get("seriesMatches") or []:
                            wrapper_matches = series.get("seriesAdWrapper", {}).get("matches") or series.get("matches") or []
                            for m in wrapper_matches:
                                if "matchInfo" in m:
                                    m_id = m["matchInfo"].get("matchId")
                                    if not any(existing.get("matchInfo", {}).get("matchId") == m_id for existing in all_matches):
                                        all_matches.append(m)
        except Exception:
            pass
    return all_matches

def handle_cricket_query(user_msg):
    msg_lower = user_msg.lower().strip()
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
        "Cache-Control": "no-cache"
    }
    
    all_matches = get_all_api_matches(headers)
    if not all_matches:
        return "সার্ভারে সমস্যা বা এই মুহূর্তে কোনো ম্যাচ চলছে না।"

    is_general_query = msg_lower in ["score", "live", "cricbuzz", "cricket"]
    is_id_query = msg_lower.isdigit()
    
    if is_general_query:
        reply = "🏆 Cricket Matches (Live & Recent):\n\n"
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
                reply += f"🏏 {score_str}\n"
            reply += f"📌 {status}\n"
            reply += f"🔑 Details dekhte likhun: {match_id}\n\n"
            
            count += 1
            if count >= 3:
                break
        return reply.strip()

    target_match = None
    if is_id_query:
        for m in all_matches:
            if str(m.get("matchInfo", {}).get("matchId")) == msg_lower:
                target_match = m
                break
    else:
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

    info = target_match.get("matchInfo") or {}
    target_match_id = info.get("matchId")
    base_status = info.get("status", "")
    match_state = info.get("state", "")
    
    if match_state in ["Complete", "Result"]:
        url_scard = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/scard"
        score_resp = requests.get(url_scard, headers=headers, timeout=10)
        
        if score_resp.status_code == 200:
            return extract_full_scorecard(score_resp.json(), base_status)
        else:
            return f"📌 {base_status}\n\n❌ Score details unavailable."
            
    else:
        t1_name = info.get("team1", {}).get("teamName", "Team 1")
        t2_name = info.get("team2", {}).get("teamName", "Team 2")
        t1_sname = info.get("team1", {}).get("teamSName", "")
        t2_sname = info.get("team2", {}).get("teamSName", "")
        
        reply = f"🏆 {t1_name} vs {t2_name}\n"
        
        url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
        score_resp = requests.get(url_live_score, headers=headers, timeout=10)
        main_score_str = get_score_str(target_match.get("matchScore"), t1_sname, t2_sname)

        if score_resp.status_code == 200:
            reply += extract_live_details(score_resp.json(), base_status, main_score_str)
        else:
            reply += f"📌 {base_status}\n\n"
            if main_score_str:
                reply += f"📊 Score:\n{main_score_str}"
                
        return reply.strip()

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    
    if len(message_text) > 1900:
        parts = [message_text[i:i+1900] for i in range(0, len(message_text), 1900)]
        for part in parts:
            payload = {"recipient": {"id": recipient_id}, "message": {"text": part}}
            requests.post(url, headers=headers, json=payload)
    else:
        payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
        requests.post(url, headers=headers, json=payload)

@app.route("/", methods=["GET"])
def index():
    return "Cricket Bot is running smoothly with Live & Completed Match Logic!", 200

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
                    
                    keywords = ["score", "live", "cricbuzz", "cricket", "ban", "afg", "bd", "sa", "aus", "ind", "eng", "pak", "nz", "vs", "wi", "zim", "sl"]
                    
                    if any(keyword in message_text.lower() for keyword in keywords) or message_text.isdigit():
                        live_score_reply = handle_cricket_query(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "Live score বা Match details জানতে 'score' লিখুন অথবা Match ID দিন।")
                        
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
