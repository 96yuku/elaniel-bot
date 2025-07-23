import discord
from openai import OpenAI
import random
import os
from collections import defaultdict, deque
import asyncio
import edge_tts
import uuid
import langdetect
import re

# Pinecone imports
from pinecone import Pinecone, ServerlessSpec

# ------------ CONFIGURE THESE -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")

TRIGGER_WORDS = ["elaniel", "el", "エル"]
ALLOWED_ROLE_NAME = "El's friend"
OWNER_USER_ID = 178453871700475904
SPECIAL_CHANNEL_ID = 1391562642019323936
LOG_CHANNEL_ID = 1391562642019323936
INDEX_NAME = "elaniel-memory"
DIMENSION = 1536
# ------------------------------------------

def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def load_lines(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

SYSTEM_PROMPT_AURI = load_prompt("el_auri_prompt.txt")
SYSTEM_PROMPT_FRIEND = load_prompt("el_friend_prompt.txt")
SYSTEM_PROMPT_OTHER = load_prompt("el_other_prompt.txt")

listening_statuses = load_lines("el_listening_statuses.txt")
dm_denials = load_lines("el_dm_denials.txt")

client_openai = OpenAI(api_key=OPENAI_API_KEY)

pc = Pinecone(api_key=PINECONE_API_KEY)

if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT or "us-east-1")
    )

index = pc.Index(INDEX_NAME)

user_memory = defaultdict(lambda: deque(maxlen=10))

async def status_cycler():
    await client.wait_until_ready()
    while not client.is_closed():
        shuffled_statuses = listening_statuses[:]
        random.shuffle(shuffled_statuses)
        for status in shuffled_statuses:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await asyncio.sleep(600)

def add_memory(user_id: str, text: str):
    try:
        embedding_response = client_openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = embedding_response.data[0].embedding
        vector_id = f"{user_id}-{uuid.uuid4()}"
        index.upsert(vectors=[(vector_id, embedding, {"text": text, "user_id": user_id})])
    except Exception as e:
        print(f"[Pinecone] Failed to add memory: {e}")

def query_memory(user_id: str, query: str, top_k=3):
    try:
        embedding_response = client_openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding

        results = index.query(queries=[query_embedding], top_k=top_k, include_metadata=True)
        matches = results.results[0].matches
        user_results = [match.metadata["text"] for match in matches if match.metadata.get("user_id") == user_id]
        return user_results
    except Exception as e:
        print(f"[Pinecone] Failed to query memory: {e}")
        return []

def delete_memory(user_id: str):
    try:
        results = index.describe_index_stats()
        if results.get("total_vector_count", 0) > 0:
            query_result = index.query(queries=[[0.0]*DIMENSION], top_k=1000, include_metadata=True)
            matches = query_result.results[0].matches
            user_ids = [m.id for m in matches if m.metadata.get("user_id") == user_id]
            if user_ids:
                index.delete(ids=user_ids)
                print(f"[Pinecone] Deleted {len(user_ids)} memory vectors for user {user_id}")
    except Exception as e:
        print(f"[Pinecone] Failed to delete memory: {e}")

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

        memories = query_memory(str(user.id), prompt, top_k=3)
        memories_text = "\n".join(memories) if memories else ""

        full_prompt = f"{system_prompt}\nRelevant memories:\n{memories_text}\nUser says: {prompt}"

        messages = [{"role": "system", "content": full_prompt}]

        if include_memory:
            for role_, content in user_memory[user.id]:
                messages.append({"role": role_, "content": content})

        messages.append({"role": "user", "content": prompt})

        response = client_openai.chat.completions.create(
            model=model,
            messages=messages
        )
        reply = response.choices[0].message.content.strip()

        if include_memory:
            user_memory[user.id].append(("user", prompt))
            user_memory[user.id].append(("assistant", reply))

        add_memory(str(user.id), prompt)

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
            voice="echo",
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
                        f"\U0001F4E5 **Unauthorized DM Attempt**\n"
                        f"From: {message.author} (`{message.author.id}`)\n"
                        f"Message: {message.content}"
                    )
            except Exception as e:
                print(f"Failed to log DM attempt: {e}")

            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    if message.guild:
        if content.startswith("el wipe memory"):
            match = re.match(r"el wipe memory\s*<?@?(\d+)>?", content)
            if match and match.group(1):
                target_id = int(match.group(1))
                if message.author.id == OWNER_USER_ID:
                    user_memory[target_id].clear()
                    delete_memory(str(target_id))
                    await message.channel.send(f"Wiped memory for <@{target_id}>.")
                else:
                    await message.channel.send("You can't wipe someone else's memory.")
            else:
                user_memory[message.author.id].clear()
                delete_memory(str(message.author.id))
                await message.channel.send("Your memory has been wiped.")
            return

        if content.startswith("el show memory"):
            if message.author.id == OWNER_USER_ID:
                parts = message.content.split()
                if len(parts) >= 4:
                    arg = parts[3]
                    target_user = None

                    mention_match = re.match(r'<@!?(\d+)>', arg)
                    if mention_match:
                        user_id = int(mention_match.group(1))
                        target_user = message.guild.get_member(user_id)
                    else:
                        try:
                            user_id = int(arg)
                            target_user = message.guild.get_member(user_id)
                        except:
                            pass

                    if target_user:
                        history = user_memory.get(target_user.id, [])
                        if not history:
                            await message.channel.send(f"Memory for {target_user} is empty.")
                        else:
                            formatted = "\n".join([f"**{r}**: {c}" for r, c in history])
                            await message.channel.send(f"Memory for {target_user}:\n{formatted}")
                    else:
                        await message.channel.send("User not found or invalid mention/ID.")
                    return
                else:
                    history = user_memory[message.author.id]
                    if not history:
                        await message.channel.send("Memory is currently empty.")
                    else:
                        formatted = "\n".join([f"**{r}**: {c}" for r, c in history])
                        await message.channel.send(f"Current memory:\n{formatted}")
                    return

            elif any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
                history = user_memory[message.author.id]
                if not history:
                    await message.channel.send("Memory is currently empty.")
                else:
                    formatted = "\n".join([f"**{r}**: {c}" for r, c in history])
                    await message.channel.send(f"Current memory:\n{formatted}")
                return
            else:
                await message.channel.send("You do not have permission to view others' memory.")
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
