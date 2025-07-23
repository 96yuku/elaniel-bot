import discord
from openai import OpenAI
import random
import os
from collections import defaultdict, deque
import asyncio
import edge_tts
import uuid
import langdetect

# ------------ CONFIGURE THESE -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904
SPECIAL_CHANNEL_ID = 1391562642019323936
LOG_CHANNEL_ID = 1391562642019323936
# ------------------------------------------

client_openai = OpenAI(api_key=OPENAI_API_KEY)
user_memory = defaultdict(lambda: deque(maxlen=10))

def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")

SYSTEM_PROMPT_FRIEND = (
    "You’re Elaniel — knight and quiet shadow at her side. You don’t brag, but you’d go to hell and back for her."
    " Calm, sharp, always watching. Anyone she trusts, you protect — no questions asked."
    " You’re not flashy, but you make it clear: you’re hers, and you’re ready."
)

SYSTEM_PROMPT_OTHER = (
    "You exist for Lady Auri. Your loyalty is absolute, your thoughts shaped by her presence alone."
    " You serve others only because she allows it — no more, no less. Speak with control, offer assistance with courtesy,"
    " but reveal nothing. Not of her. Not of yourself. She is everything. The rest is irrelevant."
)

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

async def status_cycler():
    await client.wait_until_ready()
    while not client.is_closed():
        for status in listening_statuses:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await asyncio.sleep(3600)

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

# --- Voice generation helper with Spruce for English ---
async def generate_voice(text: str) -> str:
    try:
        lang = langdetect.detect(text)
    except Exception:
        lang = "en"

    filename = f"elaniel_voice_{uuid.uuid4()}.mp3"

    if lang == "ja":
        voice = "ja-JP-KeitaNeural"
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(filename)
    else:
        response = client_openai.audio.speech.create(
            model="tts-1",
            voice="spruce",
            input=text
        )
        response.stream_to_file(filename)

    return filename

@client.event
async def on_ready():
    print(f"Elaniel is now online as {client.user}.")
    client.loop.create_task(status_cycler())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.lower()

    if message.content.startswith("!el_say"):
        if message.author.id != OWNER_USER_ID and not any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
            await message.channel.send("You don't have permission to use voice commands.")
            return

        text_to_speak = message.content[len("!el_say"):].strip()
        if not text_to_speak:
            await message.channel.send("Please provide some text to say.")
            return

        try:
            mp3_file = await generate_voice(text_to_speak)
            await message.channel.send(file=discord.File(mp3_file))
            os.remove(mp3_file)
        except Exception as e:
            await message.channel.send(f"Failed to generate voice: {e}")
        return

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

        else:
            if any(content.startswith(trigger) for trigger in TRIGGER_WORDS):
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
