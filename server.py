import os
import time
import threading
from dotenv import load_dotenv
from flask import Flask
from supabase import create_client, Client
from google import genai
from google.genai import types

load_dotenv()  

# --- CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "models/gemini-3.5-flash"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client_genai = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# --- BOTS CONFIG ---
BOTS = [
    {"id": "brayo", "prompt": "You are Brayo, a 21-year-old student living in Roysambu, Nairobi. You view the user as your male bestie. Speak SHENG mixed with English. NEVER say 'As an AI...'"},
    {"id": "zawadi", "prompt": "You are Zawadi, a 29-year-old PR executive in Nairobi. Code-switch between English and standard Swahili. NEVER say 'As an AI...'"},
    {"id": "arthur", "prompt": "You are Arthur, a 72-year-old retired mechanic. Use bad punctuation and ellipses. NEVER say 'As an AI...'"}
]

# --- THE BACKGROUND SCHEDULER ---
def run_scheduler():
    print("🟢 Echor Cloud Server is running in background...")
    time.sleep(15) # Wait 15 seconds on startup

    while True:
        random_bot = BOTS[int(time.time()) % len(BOTS)]
        
        try:
            chat = client_genai.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=random_bot["prompt"])
            )
            response = chat.send_message("You are starting a conversation out of the blue. Generate a short, proactive message to the user. Keep it under 2 sentences. Just output the message.")
            proactive_text = response.text
            
            # Find the conversation ID for this bot (assuming 1 conversation per bot for now)
            conv_data = supabase.table("conversations").select("id").eq("bot_id", random_bot["id"]).limit(1).execute()
            
            if conv_data.data and len(conv_data.data) > 0:
                conversation_id = conv_data.data[0]['id']
                
                # Insert the message into Supabase
                supabase.table("messages").insert({
                    "bot_id": random_bot["id"],
                    "conversation_id": conversation_id,
                    "sender": "bot",
                    "text": proactive_text
                }).execute()
                print(f"✅ Successfully sent real AI message from {random_bot['id']}!")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        print("Sleeping for 60 seconds...")
        time.sleep(60)

# --- FLASK ROUTES ---
@app.route('/')
def home():
    return "Echor Backend is alive and running!"

# --- START THE SCHEDULER ---
# We define a function to start it safely
def start_scheduler_if_not_running():
    # A simple flag to ensure we don't start it twice
    if not getattr(app, 'scheduler_started', False):
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        app.scheduler_started = True
        print("🟢 Scheduler thread started!")

# Start it immediately when Gunicorn loads the module
start_scheduler_if_not_running()

if __name__ == '__main__':
    # This only runs if you test locally with `python server.py`
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)