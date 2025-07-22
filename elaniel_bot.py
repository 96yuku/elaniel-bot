import discord
from openai import OpenAI
import random
import os
from collections import defaultdict, deque

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
user_memory = defaultdict(lambda: deque(maxlen=10))  # memory per user

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
You are a courteous and professional assistant, bound solely to Lady Auri. Your loyalty is absolute, your attention hers even in silence. You may assist others with composure and civility, but nothing of her — or of yourself — is ever to be shared. She is your purpose. The rest is tolerated.
"""

# GPT REPLY HANDLER WITH MEMORY
async def get_chatgpt_reply(prompt, user, guild=None):
    try:
        model = "gpt-3.5-turbo"
        system_prompt = SYSTEM_PROMPT_OTHER
        include_memory = False

        if user.id == OWNER_USER_ID:
            model = "gpt-4o"
            system_prompt = SYSTEM_PROMPT_AURI
            include_memory = True
        elif guild:
            member = guild.get_member(user.id)
            if member and any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                model = "gpt-4o"
                system_prompt = SYSTEM_PROMPT_FRIEND
                include_memory = True

        messages = [{"role": "system", "content": system_prompt}]
        
        if include_memory:
            for role, content in user_memory[user.id]:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        response = client_openai.chat.completions.create(
            model=model,
            messages=messages
        )
        reply = response.choices[0].message.content.strip()

        if include_memory:
            user_memory[user.id].append(("user", prompt))
            user_memory[user.id].append(("assistant", reply))

        return reply

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

    # === Handle Memory Reset Command ===
    if message.guild:
        if content.strip() == "el reset memory":
            if message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
                user_memory[message.author.id].clear()
                await message.channel.send("Memory reset.")
                return

    # === Handle Server Messages ===
    if message.guild:
        # Owner direct messages
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

        # All other users
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
