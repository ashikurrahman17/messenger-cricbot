import requests

def get_detailed_live_score(user_msg):
    # আপনার RapidAPI Key এবং Host এখানে বসান
    headers = {
        "x-rapidapi-key": "84979f4188mshaf1d97ff6398457p1d4d3djsn974c4fcce480",
        "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com"
    }
    
    # ধাপ ১: প্রথমে লাইভ ম্যাচগুলোর লিস্ট আনা
    url_live_matches = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    
    try:
        response = requests.get(url_live_matches, headers=headers, timeout=10)
        if response.status_code != 200:
            return "এ মুহূর্তে স্কোর পাওয়া যাচ্ছে না।"
            
        data = response.json()
        matches = data.get("typeMatches", [])
        
        target_match_id = None
        target_match_name = ""
        
        # আপনার কাঙ্ক্ষিত ইন্টারন্যাশনাল ম্যাচটি খুঁজছি (যেমন: BAN vs AFG)
        for t in matches:
            if t.get("matchType") == "International":
                for series in t.get("seriesMatches", []):
                    m_list = series.get("seriesAdWrapper", {}).get("matches", [])
                    if not m_list:
                        m_list = series.get("matches", [])
                        
                    for m in m_list:
                        info = m.get("matchInfo", {})
                        team1 = info.get("team1", {}).get("teamSName", "").lower()
                        team2 = info.get("team2", {}).get("teamSName", "").lower()
                        
                        # যদি ইউজার "ban", "afg", "bd" লিখে, তবে ম্যাচটি ধরবে
                        if "ban" in user_msg.lower() or "afg" in user_msg.lower():
                            if team1 in ["ban", "afg"] or team2 in ["ban", "afg"]:
                                target_match_id = info.get("matchId")
                                target_match_name = f"{info.get('team1', {}).get('teamName')} vs {info.get('team2', {}).get('teamName')}"
                                break
                    if target_match_id:
                        break
            if target_match_id:
                break
                
        if not target_match_id:
            return "আপনার কাঙ্ক্ষিত ম্যাচটি এখন চলছে না।"
            
        # ধাপ ২: matchId দিয়ে ব্যাটার ও বোলারের বিস্তারিত লাইভ স্কোর আনা
        url_live_score = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{target_match_id}/livescore"
        
        score_resp = requests.get(url_live_score, headers=headers, timeout=10)
        score_data = score_resp.json()
        
        # JSON থেকে ডেটা এক্সট্রাক্ট করা
        miniscore = score_data.get("miniscore", {})
        bat_team = miniscore.get("batTeam", {})
        match_status = miniscore.get("matchScoreDetails", {}).get("customStatus", "Match in progress")
        
        reply = f"🏏 {target_match_name}\n"
        reply += f"📌 {match_status}\n\n"
        
        # ব্যাটারদের তথ্য (striker এবং non-striker)
        striker = miniscore.get("striker", {})
        non_striker = miniscore.get("nonStriker", {})
        
        reply += "🏏 Batting:\n"
        if striker:
            reply += f"👉 {striker.get('batName')}*: {striker.get('batRuns')} ({striker.get('batBalls')})\n"
        if non_striker:
            reply += f"   {non_striker.get('batName')}: {non_striker.get('batRuns')} ({non_striker.get('batBalls')})\n\n"
            
        # বোলারদের তথ্য
        bowler = miniscore.get("bowler", {})
        reply += "⚾ Bowling:\n"
        if bowler:
            reply += f"👉 {bowler.get('bowlName')}: {bowler.get('bowlWkts')}/{bowler.get('bowlRuns')} ({bowler.get('bowlOvs')} ov)\n"
            
        # বর্তমান পার্টনারশিপ এবং লাস্ট কয়েক বলের স্ট্যাটাস
        reply += f"\n🤝 Partnership: {miniscore.get('partnerShip', 'N/A')}"
        
        return reply

    except Exception as e:
        print(f"API Error: {e}")
        return "সার্ভারে সমস্যা, একটু পর চেষ্টা করুন।"