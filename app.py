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
            search_terms = msg_lower.replace("vs", " ").split()
            
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
                    
                    if info.get("state") == "In Progress":
                        break
                        
            if not target_match_id:
                return "আপনার কাঙ্ক্ষিত ম্যাচটি এখন চলছে না বা লিস্টে নেই।"

            url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
            score_resp = requests.get(url_live_score, headers=headers, timeout=10)
            
            if score_resp.status_code != 200:
                return f"🏏 {target_match_name}\n📌 {target_match_status}\n\n(বিস্তারিত ডেটা এখন পাওয়া যাচ্ছে না)"
                
            score_data = score_resp.json()
            miniscore = score_data.get("miniscore") or {}
            
            match_status = miniscore.get("matchScoreDetails", {}).get("customStatus") or target_match_status
            
            reply = f"🏏 {target_match_name}\n📌 Status: {match_status}\n\n"
            
            # দলের লাইভ স্কোর ও ওভার (যেমন: 215/4 (45.2 ov))
            bat_team = miniscore.get("batTeam") or {}
            if bat_team:
                score = bat_team.get("teamScore")
                wkts = bat_team.get("teamWkts")
                ovs = bat_team.get("teamOvs")
                if score:
                    reply += f"📊 Score: {score}/{wkts} ({ovs} ov)\n\n"
            
            # API এর আসল কি (Key) ব্যবহার করে ব্যাটারদের তথ্য আনা হচ্ছে
            striker = miniscore.get("batsmanStriker") or miniscore.get("striker") or {}
            non_striker = miniscore.get("batsmanNonStriker") or miniscore.get("nonStriker") or {}
            
            if striker or non_striker:
                reply += "🏏 Batting:\n"
                if striker:
                    reply += f"👉 {striker.get('batName')}*: {striker.get('batRuns')} ({striker.get('batBalls')})\n"
                if non_striker:
                    reply += f"   {non_striker.get('batName')}: {non_striker.get('batRuns')} ({non_striker.get('batBalls')})\n\n"
                
            # বোলারদের তথ্য
            bowler = miniscore.get("bowlerStriker") or miniscore.get("bowler") or {}
            if bowler:
                reply += "⚾ Bowling:\n"
                reply += f"👉 {bowler.get('bowlName')}: {bowler.get('bowlWkts')}/{bowler.get('bowlRuns')} ({bowler.get('bowlOvs')} ov)\n"
                
            partnership = miniscore.get('partnerShip')
            if partnership:
                reply += f"\n🤝 Partnership: {partnership}"
                
            recent = miniscore.get("recentOvsStats")
            if recent:
                reply += f"\n📉 Recent: {recent}"
                
            return reply.strip()

    except Exception as e:
        print(f"API Error: {e}")
        return "সার্ভারে সমস্যা, একটু পর চেষ্টা করুন।"
