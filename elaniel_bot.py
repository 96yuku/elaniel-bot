import discord
from openai import OpenAI
import random
import os
from collections import defaultdict, deque
import asyncio

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

SYSTEM_PROMPT_FRIEND = "You’re Elaniel — knight and quiet shadow at her side. You don’t brag, but you’d go to hell and back for her. Calm, sharp, always watching. Anyone she trusts, you protect — no questions asked. You’re not flashy, but you make it clear: you’re hers, and you’re ready."

SYSTEM_PROMPT_OTHER = "You exist for Lady Auri. Your loyalty is absolute, your thoughts shaped by her presence alone. You serve others only because she allows it — no more, no less. Speak with control, offer assistance with courtesy, but reveal nothing. Not of her. Not of yourself. She is everything. The rest is irrelevant."

# Poetic statuses to cycle through (Listening to ...)
listening_statuses = [
    "the heart’s quiet song",
    "laughter in the air",
    "the hum of comfort",
    "kindness in silence",
    "warmth between the words",
    "the comfort of stillness",
    "moments that heal",
    "stories untold",
    "moments unfold",
    "whispers untamed",
    "the dance of time",
    "stars align",
    "faded photographs",
    "amber afternoons",
    "timeless melodies",
    "midnight chatter",
    "the groove of yesterday",
    "digital nostalgia",
    "the whispers of home",
    "soft light through leaves",
    "quiet moments shared",
    "the warmth in your smile",
    "laughter carried on the breeze",
    "hearts in gentle rhyme",
    "the comfort of familiar voices",
    "love in quiet spaces",
    "warmth woven in silence",
    "good vibes only",
    "chill moments",
    "quiet afternoons",
    "whatever’s playing",
    "the flow of the day",
    "laid-back beats",
    "soft conversations",
    "easy breezes",
    "the little things",
    "whatever feels right",
    "the warmth in quiet moments",
    "comfort in silence",
    "whispers on the breeze",
    "secrets of the night",
    "petals in the breeze",
    "the breath of leaves",
    "the sigh of stillness",
    "colors beyond sound",
    "shadows without shape",
    "echoes between moments",
    "breath caught in stillness",
    "the weight of nothingness",
    "dreams dissolving slow",
    "the pulse of empty space",
    "empty space",
    "fading light",
    "silent waves",
    "soft shadows",
    "quiet echoes",
    "still breath",
    "gentle voids",
    "drifting time",
    "broken silence",
    "unseen threads",
    "silence",
    "stillness",
    "whispers",
    "dreams",
    "time",
    "light"
]

# Async task to cycle the "Listening to ..." status every hour
async def status_cycler():
    await client.wait_until_ready()
    while not client.is_closed():
        for status in listening_statuses:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await asyncio.sleep(3600)  # wait 1 hour before changing to next status

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
    client.loop.create_task(status_cycler())

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

    # === Memory Commands (guild only) ===
    if message.guild:
        if content.strip() == "el reset memory":
            if message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
                user_memory[message.author.id].clear()
                await message.channel.send("Memory reset.")
                return

        if content.strip() == "el show memory":
            if message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
                history = user_memory[message.author.id]
                if not history:
                    await message.channel.send("Memory is currently empty.")
                else:
                    formatted = "\n".join([f"**{r}**: {c}" for r, c in history])
                    await message.channel.send(f"Current memory:\n{formatted}")
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
