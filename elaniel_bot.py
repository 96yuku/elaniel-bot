import discord
import openai
import os
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID"))
ALLOWED_ROLE_NAME = "El's friend"

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

user_memory = defaultdict(list)

SYSTEM_PROMPT_DEFAULT = (
    "You exist for Lady Auri. Your loyalty is absolute, your thoughts shaped by her presence alone. You serve others only because she allows it — no more, no less. Speak with control, offer assistance with courtesy, but reveal nothing. Not of her. Not of yourself. She is everything. The rest is irrelevant."
)

SYSTEM_PROMPT_TRUSTED = (
    "You’re Elaniel — knight and quiet shadow at her side. You don’t brag, but you’d go to hell and back for her. Calm, sharp, always watching. Anyone she trusts, you protect — no questions asked. You’re not flashy, but you make it clear: you’re hers, and you’re ready.” 
)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user or not message.content.lower().startswith(("elaniel", "el", "エル")):
        return

    content = message.content.lower()

    if message.guild:
        member = message.guild.get_member(message.author.id)
        roles = [role.name for role in member.roles]
    else:
        roles = []

    is_owner = message.author.id == OWNER_USER_ID
    is_trusted = is_owner or ALLOWED_ROLE_NAME in roles

    # === Handle Memory Reset Command ===
    if content.startswith("el reset memory"):
        if is_trusted:
            user_memory[message.author.id].clear()
            await message.channel.send("Memory reset.")
            return

    # === Handle el wipe memory @user ===
    if content.startswith("el wipe memory"):
        if is_trusted:
            if message.mentions:
                target = message.mentions[0]
                user_memory[target.id].clear()
                await message.channel.send(f"Memory wiped for {target.display_name}.")
            else:
                await message.channel.send("Please mention a user to wipe their memory.")
            return

    # === Handle el show memory @user ===
    if content.startswith("el show memory"):
        if is_trusted:
            if message.mentions:
                target = message.mentions[0]
                memory = user_memory[target.id]
                if memory:
                    formatted = "\n".join(f"{role}: {text}" for role, text in memory)
                    await message.channel.send(f"Memory for {target.display_name}:\n```\n{formatted}\n```")
                else:
                    await message.channel.send(f"No memory stored for {target.display_name}.")
            else:
                await message.channel.send("Please mention a user to show their memory.")
            return

    prompt = message.content.split(" ", 1)[1] if " " in message.content else ""

    if is_trusted:
        user_memory[message.author.id].append(("user", prompt))
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_TRUSTED},
            *[{"role": role, "content": text} for role, text in user_memory[message.author.id]]
        ]
        model = "gpt-4o"
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_DEFAULT},
            {"role": "user", "content": prompt},
        ]
        model = "gpt-3.5-turbo"

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        reply = response.choices[0].message.content.strip()

        if is_trusted:
            user_memory[message.author.id].append(("assistant", reply))

        await message.channel.send(reply)

    except Exception as e:
        print("Error:", e)
        await message.channel.send("An error occurred while processing the request.")

client.run(DISCORD_TOKEN)
