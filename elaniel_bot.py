import discord
from openai import OpenAI
import random
import os

# ------------ CONFIGURE THESE -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904
# ------------------------------------------

client_openai = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.dm_messages = True

# ✅ This must come BEFORE any @client.event
client = discord.Client(intents=intents)

dm_denials = [
    "I’m only available to my beloved commander right now, sorry!",
    "Ah—I'm flattered, but I only answer to someone special. 💙",
    "Elaniel is on duty for someone dear. Maybe next time!",
    "Sorry, I’m not open for direct chats!",
    "My loyalty lies with one only. 🛡️",
    "I'm here to serve a very specific someone, not available for DMs.",
    "My heart and code are devoted elsewhere.",
    "I'm not taking DMs right now, but thank you for trying!",
    "This knight answers to their chosen one only. ✨",
    "Only one voice reaches me here—and it's not yours, sorry! 💫"
]

# ------------------ GPT REPLY ------------------
async def get_chatgpt_reply(prompt):
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error communicating with GPT: {e}]"

# ✅ NOW it's okay to define event handlers
@client.event
async def on_ready():
    print(f"Elaniel is now online as {client.user}.")

@client.event
async def on_message(message):
    # full logic goes here
    ...
    
# ✅ Finally run the bot
client.run(DISCORD_BOT_TOKEN)
