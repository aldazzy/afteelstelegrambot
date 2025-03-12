from telethon import TelegramClient, events, Button
import os
from datetime import datetime
import asyncio
import logging
import aiohttp
from aiohttp import web
import nest_asyncio

# Enable nested event loops (required for running both web server and Telegram client)
nest_asyncio.apply()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = '23654309'
API_HASH = '919203c2e75e361be6b831683e29c64f'
BOT_TOKEN = '7401049941:AAHdrLrZnPUFW5uPgJoGwGRkPjs7MWR9bNU'

# Updated list of news channels
NEWS_CHANNELS = ['@bbc_news', '@ReutersWorld', '@CNN', '@TheEconomist', '@business_insider']

# Directory to save news text files
SAVE_DIR = "news_articles"
os.makedirs(SAVE_DIR, exist_ok=True)

# Get port from environment variable for Render compatibility
PORT = int(os.environ.get("PORT", 8080))

# Initialize Telegram client
client = TelegramClient('afreels_news_bot', API_ID, API_HASH)

# User session storage - to track conversation state
user_states = {}

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Handler for the /start command"""
    user_id = event.sender_id
    
    # Reset user state
    user_states[user_id] = {'selected_channel': None}
    
    welcome_text = (
        "Welcome to the Afreels News Bot! 📰\n\n"
        "I can fetch today's latest news from various channels for you.\n\n"
        "Please select a news channel to continue:"
    )
    
    # Create channel selection buttons
    buttons = [Button.inline(channel, data=f"channel:{channel}") for channel in NEWS_CHANNELS]
    
    # Format buttons in rows of two
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    
    await event.respond(welcome_text, buttons=keyboard)

@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    """Handler for the /help command"""
    help_text = (
        "📌 **Afreels News Bot Help**\n\n"
        "This bot fetches today's news from selected Telegram channels and displays them as interactive cards.\n\n"
        "**Available Commands:**\n"
        "• /start - Start the bot and select a news channel\n"
        "• /fetchnews - Fetch latest news from your selected channel\n"
        "• /channels - Show available news channels\n"
        "• /help - Show this help message"
    )
    await event.respond(help_text)

@client.on(events.NewMessage(pattern='/channels'))
async def channels_command(event):
    """Handler to display available channels"""
    channels_text = "📢 **Available News Channels:**\n\n"
    channels_text += "\n".join([f"• {channel}" for channel in NEWS_CHANNELS])
    channels_text += "\n\nSelect a channel:"
    
    # Create channel selection buttons
    buttons = [Button.inline(channel, data=f"channel:{channel}") for channel in NEWS_CHANNELS]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    
    await event.respond(channels_text, buttons=keyboard)

@client.on(events.CallbackQuery(pattern=r"channel:"))
async def channel_callback(event):
    """Handle channel selection"""
    user_id = event.sender_id
    selected_channel = event.data.decode('utf-8').split(':')[1]
    
    # Store the selected channel in user state
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]['selected_channel'] = selected_channel
    
    await event.edit(f"You selected: {selected_channel}\n\nUse /fetchnews to get today's news from this channel.")

@client.on(events.NewMessage(pattern='/fetchnews'))
async def fetch_news_command(event):
    """Handler for the /fetchnews command"""
    user_id = event.sender_id
    
    # Check if user has selected a channel
    if user_id not in user_states or 'selected_channel' not in user_states[user_id] or not user_states[user_id]['selected_channel']:
        channels_buttons = [Button.inline(channel, data=f"channel:{channel}") for channel in NEWS_CHANNELS]
        keyboard = [channels_buttons[i:i+2] for i in range(0, len(channels_buttons), 2)]
        await event.respond("Please select a news channel first:", buttons=keyboard)
        return
    
    selected_channel = user_states[user_id]['selected_channel']
    
    # Inform the user that we're fetching news
    status_message = await event.respond(f"Fetching today's news from {selected_channel}... Please wait.")
    
    # Get today's date
    today = datetime.now().date()
    
    try:
        # Get messages from the selected channel
        news_count = 0
        news_items = []
        
        # Fetch the last 20 messages and filter for today's date
        async for message in client.iter_messages(selected_channel, limit=20):
            # Check if message is from today
            message_date = message.date.date()
            if message_date == today and message.text:
                news_count += 1
                news_items.append(message)
                
                # Save the news article
                file_name = f"{SAVE_DIR}/{selected_channel.replace('@', '')}_news_{message.id}.txt"
                with open(file_name, "w", encoding="utf-8") as file:
                    file.write(message.text)
        
        # Edit the status message
        await status_message.delete()
        
        if news_count == 0:
            await event.respond(f"No news found from {selected_channel} for today.")
            return
            
        await event.respond(f"Found {news_count} news items from {selected_channel} for today.")
        
        # Display each news item as a card
        for i, news_item in enumerate(news_items):
            # Limit text to a preview length
            news_text = news_item.text
            preview_text = news_text[:200] + "..." if len(news_text) > 200 else news_text
            
            # Create a card-like presentation
            card_text = (
                f"📰 **News #{i+1}** - {news_item.date.strftime('%H:%M')}\n\n"
                f"{preview_text}"
            )
            
            # Add buttons to view full content
            buttons = [
                Button.inline("View Full Article", data=f"view:{selected_channel}:{news_item.id}")
            ]
            
            await event.respond(card_text, buttons=buttons)
    
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        await event.respond(f"Error fetching news from {selected_channel}. Please try again later.")

@client.on(events.CallbackQuery(pattern=r"view:"))
async def view_full_article(event):
    """Handler to show full article content"""
    data_parts = event.data.decode('utf-8').split(':')
    channel = data_parts[1]
    message_id = int(data_parts[2])
    
    try:
        # Fetch the specific message
        message = await client.get_messages(channel, ids=message_id)
        
        if not message or not message.text:
            await event.respond("Sorry, this article is no longer available.")
            return
        
        # Format the full article text
        full_text = (
            f"📰 **Full Article**\n"
            f"📆 {message.date.strftime('%Y-%m-%d %H:%M')}\n"
            f"📢 {channel}\n\n"
            f"{message.text}"
        )
        
        # Split text into chunks if it's too long (Telegram has a message length limit)
        if len(full_text) > 4000:
            chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
            for chunk in chunks:
                await event.respond(chunk)
        else:
            await event.respond(full_text)
            
    except Exception as e:
        logger.error(f"Error retrieving full article: {e}")
        await event.respond("Sorry, there was an error retrieving the full article. Please try again later.")

# Create a simple web server for Render
async def handle_index(request):
    return web.Response(text="Afreels News Bot is running!")

async def handle_healthcheck(request):
    return web.Response(text="OK", status=200)

# Setup web app with routes
app = web.Application()
app.add_routes([
    web.get('/', handle_index),
    web.get('/health', handle_healthcheck)
])

async def run_web_app():
    """Run the web server"""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

async def main():
    """Main function to start both the bot and web server"""
    # Start web server
    await run_web_app()
    
    # Start Telegram bot
    await client.start(bot_token=BOT_TOKEN)
    
    # Print info to console
    me = await client.get_me()
    logger.info(f"Bot is running as @{me.username}")
    logger.info(f"Monitoring channels: {', '.join(NEWS_CHANNELS)}")
    
    # Keep the bot running
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
