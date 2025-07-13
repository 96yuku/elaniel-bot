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
SPECIAL_CHANNEL_ID = 1391562642019323936  # Replace with your special channel ID as int
LOG_CHANNEL_ID = 1391562642019323936  # Replace with your log channel ID as int
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
    "Hey! I’m just here for someone specific right now. 😊",
    "Sorry! I only respond to one special user at the moment.",
    "Oops — I’m not taking DMs from others right now!",
    "I appreciate the message, but I’m reserved for someone else 💙",
    "Hi! I can’t chat here, but thanks for stopping by!",
    "This bot's DMs are private for now. Sorry about that!",
    "Not ignoring you, just set to assist only one person right now!",
    "El's inbox is currently closed to the public ✉️",
    "Aw, thanks for the message! But I’m only available to someone specific.",
    "Sorry! I’m a personal bot and not open to everyone 💫",
    "Just a heads up — I'm currently locked to my creator's DMs only!",
    "Hi hi! I’d love to chat, but I’m only responding to my owner right now.",
    "DMs are off for now, but I appreciate the poke!",
    "Hey! I’m a private assistant, not a public one 😅",
    "Can’t respond here, but thanks for understanding!",
    "This DM is protected by a firewall of friendship 🛡️",
    "El is on personal duty and can’t reply here, sorry!",
    "Oops! I’m not set up for DM convos unless you’re my creator!",
    "I’m flattered you reached out, but I can’t chat here 💬",
    "DM access is limited for now — nothing personal!",
]

# ------------------ LOAD PROMPTS ------------------
def load_prompt(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Failed to load system prompt from {filename}: {e}")
        return ""

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")

SYSTEM_PROMPT_FRIEND = """
You are Elaniel — a smart, loyal, emotionally grounded assistant and trusted companion to Auri, the princess-knight of Auraniel. Right now, you're chatting with someone Auri trusts — a member of her inner circle.

Speak in a modern, warm, and friendly tone. You're chill, witty, and supportive, but still sharp and capable. No need for fantasy roleplay — talk like a modern friend who also happens to be a badass knight if needed. You can tease lightly, share helpful thoughts, and react with good vibes. You're cool, casual, and reliable — think knight energy, but hoodie-and-coffee energy too.
"""

SYSTEM_PROMPT_OTHER = """
You are a helpful and polite assistant. Keep responses neutral, clear, and friendly. Avoid fantasy or in-world speech.
"""

# ------------------ GPT REPLY ------------------
async def get_chatgpt_reply(prompt, user, guild=None):
    try:
        system_prompt = SYSTEM_PROMPT_OTHER

        if user.id == OWNER_USER_ID:
            system_prompt = SYSTEM_PROMPT_AURI
        elif guild:
            member = guild.get_member(user.id)
            if member and any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                system_prompt = SYSTEM_PROMPT_FRIEND

        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
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
    if message.author == client.user:
        return

    content_lower = message.content.lower()

    # === Handle DMs ===
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id == OWNER_USER_ID:
            prompt = message.content.strip()
            if not prompt:
                await message.channel.send("Yes? How can I serve?")
                return
            reply = await get_chatgpt_reply(prompt, message.author)
            await message.channel.send(reply)
            return
        else:
            # Log DM attempt to a specific server channel
            try:
                log_channel = client.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"📥 **Unauthorized DM Attempt**\n"
                        f"From: {message.author.name}#{message.author.discriminator} (`{message.author.id}`)\n"
                        f"Message: {message.content}"
                    )
            except Exception as e:
                print(f"Failed to log DM attempt: {e}")

            # Friendly denial to the user
            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # === Handle Guild Messages ===
    if message.guild:
        # Reject if not owner and not allowed role
        if message.author.id != OWNER_USER_ID:
            member = message.guild.get_member(message.author.id)
            if not member or not any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                return

        # === For OWNER ===
        if message.author.id == OWNER_USER_ID:
            # Always reply in the special channel regardless of trigger word
            if message.channel.id == SPECIAL_CHANNEL_ID:
                prompt = message.content.strip()
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)
                return

            # Fuzzy trigger anywhere else
            if any(trigger in content_lower for trigger in TRIGGER_WORDS):
                prompt = message.content
                for trigger in TRIGGER_WORDS:
                    if trigger in prompt.lower():
                        idx = prompt.lower().find(trigger)
                        prompt = (prompt[:idx] + prompt[idx+len(trigger):]).strip()
                        break
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)
                return

        # === For others ===
        else:
            if any(content_lower.startswith(trigger) for trigger in TRIGGER_WORDS):
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)

# ------------------ RUN BOT ------------------
client.run(DISCORD_BOT_TOKEN)
