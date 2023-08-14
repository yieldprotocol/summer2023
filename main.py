import os
import json
import discord
import requests
import urllib.parse
from urllib.parse import quote
from discord.ext import commands
from search import search_question
from dotenv import load_dotenv
load_dotenv()

LAMBDA_URL = os.getenv('LAMBDA_URL')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MAX_LENGTH = 2000

headers = {"Content-Type": "application/json"}

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def format_yield_prompt(query, relevant_documents):
    instruction = f"%%% Instruction\n{query}"
    docs = '\n'.join(relevant_documents)
    context = f"%%% Context\n{docs}"
    response = f"%%% Answer"
    # join all the parts together
    prompt = "\n\n".join([i for i in [instruction, context, response] if i is not None])
    return prompt

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Check if the bot is mentioned
    if bot.user.mentioned_in(message):
        # You can extract the query from the message content
        # For example, you might remove the mention from the beginning of the message
        author_mention = message.author.mention
        query = message.content.replace(f'<@!{bot.user.id}> ', '')
        search_results = search_question(query)
        prompt = format_yield_prompt(query, search_results)

        # Your Lambda URL
        url = LAMBDA_URL

        # URL-encode the query to the actual format, around 3k tokens max, could be errorneous
        encoded_query = urllib.parse.quote(prompt)
        full_url = f"{url}?query={encoded_query}"

        # Send GET request to your Lambda function
        response = requests.get(full_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response
            answer = json.loads(response.text)

            # mention the caller 
            full_answer = f"{author_mention}: {answer}"

            # chunk the message in case of run-on.
            answer_chunks = [full_answer[i:i+MAX_LENGTH] for i in range(0, len(full_answer), MAX_LENGTH)]

            # Send each chunk as a separate message
            for chunk in answer_chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(f"An error occurred while processing your request. ERROR CODE: {response.status_code}")

# Replace 'YOUR_TOKEN_HERE' with your bot's token
bot.run(DISCORD_TOKEN)