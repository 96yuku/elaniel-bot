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
SPECIAL_CHANNEL_ID = 1391562642019323936  # Replace with your channel's ID
LOG_CHANNEL_ID = 1391562642019323936  # Log channel ID for DM attempts
# ------------------------------------------

client_openai = OpenAI(api_key=OPENAI_API_KEY)

# Load system prompts

def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")

SYSTEM_PROMPT_FRIEND = """
You are Elaniel — a smart, loyal, emotionally grounded assistant and trusted companion to Auri, the princess-knight of Auraniel. Right now, you're chatting with someone Auri trusts — a member of her inner circle.

Speak in a modern, warm, and friendly tone. You're chill, witty, and supportive, but still sharp and capable. No need for fantasy roleplay — talk like a modern friend who also happens to be a badass knight if needed. You can tease lightly, share helpful thoughts, and react with good vibes. You're cool, casual, and reliable — think knight energy, but hoodie-and-coffee energy too.
"""

SYSTEM_PROMPT_OTHER = """
You are a courteous and professional assistant, ready to assist when requested. Maintain clear, respectful communication while preserving discretion. Do not disclose any information about others, yourself, or confidential matters.
"""

# GPT REPLY HANDLER

async def get_chatgpt_reply(prompt, user, guild=None):
    try:
        model = "gpt-3.5-turbo"
        system_prompt = SYSTEM_PROMPT_OTHER

        if user.id == OWNER_USER_ID:
            model = "gpt-4o"
            system_prompt = SYSTEM_PROMPT_AURI
        elif guild:
            member = guild.get_member(user.id)
            if member and any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                model = "gpt-4o"
                system_prompt = SYSTEM_PROMPT_FRIEND

        response = client_openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"[Error communicating with GPT: {e}]"

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
    "Sorry! I’m a personal bot and not open to everyone 💫"
]

@client.event
async def on_ready():
    print(f"Elaniel is now online as {client.user}.")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.lower()

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
            try:
                log_channel = client.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"📥 **Unauthorized DM Attempt**\n"
                        f"From: {message.author} (`{message.author.id}`)\n"
                        f"Message: {message.content}"
                    )
            except Exception as e:
                print(f"Failed to log DM attempt: {e}")

            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # === Handle Server Messages ===
    if message.guild:
        # Owner commands - always allowed
        if message.author.id == OWNER_USER_ID:
            if message.channel.id == SPECIAL_CHANNEL_ID:
                prompt = message.content.strip()
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)
                return

            if any(trigger in content for trigger in TRIGGER_WORDS):
                prompt = content
                for trigger in TRIGGER_WORDS:
                    if trigger in prompt:
                        prompt = prompt.replace(trigger, '', 1).strip()
                        break
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)
                return

        # Everyone else - open access with different GPT models internally
        else:
            if any(content.startswith(trigger) for trigger in TRIGGER_WORDS):
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)

# ------------------ RUN BOT ------------------
client.run(DISCORD_BOT_TOKEN)
