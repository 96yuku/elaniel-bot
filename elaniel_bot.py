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
LOG_CHANNEL_ID = 1391562642019323936

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
        reply = await get_chatgpt_reply(prompt)
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
        if message.author.id != OWNER_USER_ID:
            member = message.guild.get_member(message.author.id)
            if not member or not any(role.name == ALLOWED_ROLE_NAME for role in member.roles):
                return

        # === For you ===
        if message.author.id == OWNER_USER_ID:
            # ✅ Always reply in special channel
            if message.channel.id == SPECIAL_CHANNEL_ID:
                prompt = message.content.strip()
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt)
                await message.channel.send(reply)
                return

            # ✅ Fuzzy trigger anywhere in other channels
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

        # === For others ===
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
