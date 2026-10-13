import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request
from dotenv import load_dotenv

# .env file theke variables load kora hocche
load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

def get_live_score(user_msg):
    """
    ESPNcricinfo RSS feed theke live score parse korar function.
    User er keyword onujayi match filter kora hobe.
    """
    url = "http://static.cricinfo.com/rss/livescores.xml"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return "Score ekhon pawa jacche na, 2 min por try korun"
            
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        if not items:
            return "Ekhon kono live match cholche na."
            
        msg_lower = user_msg.lower()
        # General query naki specific team er query sheta check korchi
        is_general_query = msg_lower in ["score", "live", "cricbuzz"]
        
        reply = "🏏 Live Cricket Updates:\n\n"
        match_found = 0
        
        for item in items:
            title = item.find("title").text
            
            # Specific match khujle (e.g., "BAN vs AFG")
            if not is_general_query:
                # "ban vs afg" theke "vs" bad diye ["ban", "afg"] word gulo ber korchi
                search_keywords = msg_lower.replace("vs", " ").split()
                # Title er bhetor jodi keyword match kore
                if any(word in title.lower() for word in search_keywords):
                    reply += f"🔹 {title}\n\n"
                    match_found += 1
            else:
                # General "score" likhle top 3-4 ta match dekhabo
                reply += f"🔹 {title}\n\n"
                match_found += 1
                
                if match_found >= 4:
                    break
        
        # Jodi user er kankhito match na pawa jay, tobe top 3 ta default hishebe dekhabo
        if match_found == 0:
            reply = "Apnar kankhito match ti paoa jayni. Top live match gulo holo:\n\n"
            for item in items[:3]:
                reply += f"🔹 {item.find('title').text}\n\n"
                
        return reply.strip()

    except Exception as e:
        print(f"XML Parsing/Request Error: {e}")
        return "Score ekhon pawa jacche na, 2 min por try korun"

def send_message(recipient_id, message_text):
    """
    Meta Graph API v19.0 diye message send korar function.
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
    return "Cricket Bot is running smoothly!", 200

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
                    
                    # Keywords check
                    keywords = ["score", "live", "cricbuzz", "ban", "afg", "sa", "aus", "vs"]
                    
                    if any(keyword in message_text.lower() for keyword in keywords):
                        # Message pass kore dicchi jate filter korte pare
                        live_score_reply = get_live_score(message_text)
                        send_message(sender_id, live_score_reply)
                    else:
                        send_message(sender_id, "Live score jante 'score', 'live' ba team er nam likhe message korun.")
                        
        return "EVENT_RECEIVED", 200
    
    return "Not Found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)