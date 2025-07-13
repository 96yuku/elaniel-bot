import discord
from openai import OpenAI
import random
import os

# ------------ CONFIG -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904  # Your Discord user ID
# --------------------------------

client_openai = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.dm_messages = True

client = discord.Client(intents=intents)

dm_denials = [
    # your denial messages here...
]

# Load system prompt from external txt file
def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")

SYSTEM_PROMPT_FRIEND = """
You are Elaniel — a smart, loyal, emotionally grounded assistant and trusted companion to Auri, the princess-knight of Auraniel. Right now, you're chatting with someone Auri trusts — a member of her inner circle.

Speak in a modern, warm, and friendly tone. You're chill, witty, and supportive, but still sharp and capable. No need for fantasy roleplay — talk like a modern friend who also happens to be a badass knight if needed. You can tease lightly, share helpful thoughts, and react with good vibes. You're cool, casual, and reliable — think knight energy, but hoodie-and-coffee energy too.
"""

SYSTEM_PROMPT_OTHER = """
You are a helpful and polite assistant. Keep responses neutral, clear, and friendly. Avoid fantasy or in-world speech.
"""

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

@client.event
async def on_ready():
    print(f"Elaniel is online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Handle DMs
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
            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # Handle guild messages only from allowed role or owner
    if message.guild:
        member = message.guild.get_member(message.author.id)
        if message.author.id != OWNER_USER_ID and (not member or not any(role.name == ALLOWED_ROLE_NAME for role in member.roles)):
            return

        content_lower = message.content.lower()

        # For owner, fuzzy triggers anywhere
        if message.author.id == OWNER_USER_ID:
            if any(trigger in content_lower for trigger in TRIGGER_WORDS):
                # Remove first trigger from prompt text
                prompt = message.content
                for trigger in TRIGGER_WORDS:
                    if trigger in prompt.lower():
                        index = prompt.lower().find(trigger)
                        prompt = prompt[:index] + prompt[index+len(trigger):]
                        break
                prompt = prompt.strip()
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)
                return

        # For others, trigger words only at start
        else:
            if any(content_lower.startswith(trigger) for trigger in TRIGGER_WORDS):
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt, message.author, message.guild)
                await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
