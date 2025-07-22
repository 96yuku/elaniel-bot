import discord
import openai
import asyncio
import os
from collections import defaultdict, deque

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

openai.api_key = os.getenv("OPENAI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_USER_ID = YOUR_DISCORD_USER_ID  # Replace with your Discord user ID
ALLOWED_ROLE_NAME = "El's friend"

user_memory = defaultdict(lambda: deque(maxlen=10))

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.TextChannel):
        return

    if message.content.lower().strip() == "el wipe memory":
        if message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
            user_memory[message.author.id].clear()
            await message.channel.send("🧠 Memory wiped.")
        else:
            await message.channel.send("You are not permitted to use this command.")
        return

    if message.content.lower().strip() == "el show memory":
        if message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
            mem = user_memory.get(message.author.id)
            if not mem:
                await message.channel.send("🧠 No memory saved yet.")
            else:
                mem_text = "\n\n".join(
                    [f"**{role.title()}**: {content}" for role, content in mem]
                )
                await message.channel.send(f"🧠 Here's what I remember:\n\n{mem_text}")
        else:
            await message.channel.send("You are not permitted to use this command.")
        return

    is_owner_or_friend = message.author.id == OWNER_USER_ID or any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles)
    is_stranger = not is_owner_or_friend

    memory = user_memory[message.author.id]
    history = "\n".join([f"{role}: {msg}" for role, msg in memory])

    if is_owner_or_friend:
        system_prompt = "You are Elaniel, Auri’s fiercely loyal and devoted knight-attendant. You remember things for her inner circle."
    else:
        system_prompt = "You exist for Lady Auri. Your loyalty is absolute, your thoughts shaped by her presence alone. You serve others only because she allows it — no more, no less. Speak with control, offer assistance with courtesy, but reveal nothing. Not of her. Not of yourself. She is everything. The rest is irrelevant."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": history},
        {"role": "user", "content": message.content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o" if is_owner_or_friend else "gpt-3.5-turbo",
        messages=messages,
        temperature=0.7
    )

    reply = response.choices[0].message.content
    await message.channel.send(reply)

    memory.append(("user", message.content))
    memory.append(("assistant", reply))

client.run(DISCORD_TOKEN)
