import discord
from openai import OpenAI
import os

# CONFIG
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_USER_ID = 178453871700475904  # Replace with your actual Discord user ID

# Load system prompt from file
def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")
print("----- System Prompt Preview -----")
print(SYSTEM_PROMPT_AURI[:500])  # print first 500 chars
print("----- End Preview -----")

# Setup Discord client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)
client_openai = OpenAI(api_key=OPENAI_API_KEY)

async def get_chatgpt_reply(prompt, user):
    system_prompt = SYSTEM_PROMPT_AURI if user.id == OWNER_USER_ID else "You are a helpful assistant."

    try:
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
    print(f"Bot is online as {client.user}.")

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Only respond to owner user
    if message.author.id == OWNER_USER_ID:
        prompt = message.content.strip()
        if not prompt:
            await message.channel.send("Yes? How can I serve?")
            return
        reply = await get_chatgpt_reply(prompt, message.author)
        await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
