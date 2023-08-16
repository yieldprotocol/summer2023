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

def help_message():
    ret = """
Hey there! 🦙 I'm Yield-Llama, your AI assistant for all things Yield Protocol.

✨ What I Do:
- I'm backed by LLaMA-v2, a 13-billion parameter language model.
- I know a lot about Yield Protocol's documentation, code, proposals, and papers.

🚀 How to Use Me:
- Just @ me and ask your question!
- Keep it specific to Yield Protocol for the best results.

⚠️ A Heads Up:
- I'm still in beta, so I might not always be perfect.
- I may occassionally produce incorrect, misleading information if the question is too complex or too general to the topic of asking.
- Always double-check critical information and consult with the Yield Protocol team, especially if it's related to your interest directly when using Yield Protocol.
- Currently, I'm unable to support multi-turn chatting to solve long and complex questions like *ChatGPT*. Be sure to specific everything all at once to ask.

📌 Commands:
- `!help`: Shows this message.
- `!cite`: Gets the source from our database and answers your query.
    
Happy querying!"""

    return ret

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
        print(f"full message: {message.content}")
        print(f"bot id: {bot.user.id}")
        clean_message = message.content.replace(f'<@{bot.user.id}> ', '')

        # only support 2 commands so far.
        components = clean_message.split()
        print(f".replace: {components}")

        if len(components) < 1:
            return
        
        command = components[0] # The command is the second component (after the mention)
        query = clean_message
        
        if command == '!help':
            await message.channel.send(help_message())
            return 
        # parse the command from the bot to show documents.

        send_sources = False
        if command == '!cite':
            send_sources = True
            query = ' '.join(components[1:])

        relevant_docs, relevant_srcs = search_question(query)

        if(len(relevant_docs) == 0):
            # in case the query has not searching any relevant documents
            await message.channel.send(f"I am sorry, but I could not relate any contexts in my document collection for your question *{query}*. Please consult developers or other discord users for solving your question.")
        else: 
            prompt = format_yield_prompt(query, relevant_docs)

            # Your Lambda URL, only call API if we actually find relevant documents for the question.
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
                relevant_distinct_srcs = list(set(relevant_srcs))
                cited_sources = '\n'.join([src for src in relevant_distinct_srcs])
                full_answer = f"{author_mention}: {answer}\n\n**Cited Sources: \n{cited_sources}**"
                
                if send_sources: # if need to print context to discord channel for debugging
                    form_sources = ""

                    for i in range(len(relevant_docs)):
                        form_sources += f"**Source {i+1}: {relevant_srcs[i]}**\n"
                        form_sources += f"{relevant_docs[i]}\n\n"
    
                    full_answer = f"{author_mention}: {answer}\n\n**Cited Sources**: \n{form_sources}"
                
                # chunk the message in case of run-on.
                answer_chunks = [full_answer[i:i+MAX_LENGTH] for i in range(0, len(full_answer), MAX_LENGTH)]

                # Send each chunk as a separate message
                for chunk in answer_chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(f"An error occurred while processing your request. ERROR CODE: {response.status_code}")

# Replace 'YOUR_TOKEN_HERE' with your bot's token
bot.run(DISCORD_TOKEN)