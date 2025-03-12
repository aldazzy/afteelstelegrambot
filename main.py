from telethon import TelegramClient, events
import os

# Telegram API credentials (Get from https://my.telegram.org/)
API_ID = '23654309'
API_HASH = '919203c2e75e361be6b831683e29c64f'
BOT_TOKEN = '7401049941:AAHdrLrZnPUFW5uPgJoGwGRkPjs7MWR9bNU'

# List of channels to fetch news from
NEWS_CHANNELS = ['@eliking_m', '@DailyNation']

# Directory to save news text files
SAVE_DIR = "news_articles"
os.makedirs(SAVE_DIR, exist_ok=True)

# Initialize Telegram client
client = TelegramClient('news_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    welcome_text = """Welcome to the Afreels News Bot! 📢\n\nAvailable Commands:\n/start - Show this message\n/fetchnews - Get the latest news\n/help - Get help information"""
    await event.respond(welcome_text)

@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    help_text = "This bot fetches news from selected Telegram channels and saves them as text files. Use /fetchnews to manually retrieve news."
    await event.respond(help_text)

@client.on(events.NewMessage(pattern='/fetchnews'))
async def fetch_news_command(event):
    await event.respond("Fetching the latest news... Please wait.")
    for channel in NEWS_CHANNELS:
        async for message in client.iter_messages(channel, limit=5):
            news_text = message.text
            if news_text:
                file_name = f"{SAVE_DIR}/news_{message.id}.txt"
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(news_text)
                await event.respond(f"Saved: {file_name}")

print("Bot is running...")
client.run_until_disconnected()
