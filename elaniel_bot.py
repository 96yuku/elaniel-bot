import discord
from openai import OpenAI
import random
import os

# ------------ CONFIGURE THESE -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Set this in Railway or your .env file
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Set this in Railway or your .env file
TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904  # Your Discord user ID
# ------------------------------------------

client_openai = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.dm_messages = True

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

# ------------------ MAIN EVENTS ------------------
@client.event
async def on_ready():
    print(f"Elaniel is now online as {client.user}.")

@client.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == client.user:
        return

    # Handle DMs
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id != OWNER_USER_ID:
            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # Handle guild messages only from allowed role or user
    if message.guild:
        if message.author.id != OWNER_USER_ID and not any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
            return

        content = message.content.lower()
        if any(content.startswith(t) for t in TRIGGER_WORDS):
            prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
            if not prompt:
                await message.channel.send("Yes? How can I serve?")
                return
            reply = await get_chatgpt_reply(prompt)
            await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
