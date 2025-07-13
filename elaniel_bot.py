import discord
from openai import OpenAI
import random
import os

# ------------ CONFIGURE THESE -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904  # Replace with your actual Discord user ID
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

# Replace with the channel ID where El always replies to you
SPECIAL_CHANNEL_ID = 1391562642019323936  # ← Replace this with your channel's ID as an int

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.lower()

    # Handle DMs
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id != OWNER_USER_ID:
            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # Handle guild messages
    if message.guild:
        if message.author.id != OWNER_USER_ID:
            member = message.guild.get_member(message.author.id)
            if not member or not any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                return

        # === Your messages ===
        if message.author.id == OWNER_USER_ID:
            # ✅ Always reply in the special channel (no trigger needed)
            if message.channel.id == SPECIAL_CHANNEL_ID:
                prompt = message.content.strip()
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt)
                await message.channel.send(reply)
                return

            # ✅ Elsewhere: fuzzy match
            if any(trigger in content for trigger in TRIGGER_WORDS):
                prompt = content
                for trigger in TRIGGER_WORDS:
                    if trigger in prompt:
                        prompt = prompt.replace(trigger, '', 1).strip()
                        break
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt)
                await message.channel.send(reply)
                return

        # === Others: trigger must be at the start ===
        else:
            if any(content.startswith(trigger) for trigger in TRIGGER_WORDS):
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt)
                await message.channel.send(reply)


# ------------------ RUN BOT ------------------
client.run(DISCORD_BOT_TOKEN)
