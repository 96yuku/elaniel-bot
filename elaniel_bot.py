@client.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == client.user:
        return

    # Handle DMs
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id != OWNER_USER_ID:
            denial = random.choice(dm_denials)
            await message.channel.send(denial)
            return

    # Handle guild messages only from allowed role or user
    if message.guild:
        if message.author.id != OWNER_USER_ID and not any(role.name == ALLOWED_ROLE_NAME for role in message.author.roles):
            return

        content = message.content.lower()

        if message.author.id == OWNER_USER_ID:
            # For you: trigger if any trigger word appears anywhere
            if any(trigger in content for trigger in TRIGGER_WORDS):
                # Extract prompt by removing first trigger word found (optional)
                # This is a simple way to remove the trigger word once from the start or anywhere
                # You can adjust this logic as you want
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

        else:
            # For others: only trigger if message starts with trigger word
            if any(content.startswith(trigger) for trigger in TRIGGER_WORDS):
                # Extract prompt after first word (trigger)
                prompt = message.content.split(' ', 1)[1] if ' ' in message.content else ""
                if not prompt:
                    await message.channel.send("Yes? How can I serve?")
                    return
                reply = await get_chatgpt_reply(prompt)
                await message.channel.send(reply)
