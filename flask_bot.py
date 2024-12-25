from flask import Flask, jsonify
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)
import logging
import replicate
import traceback
from dotenv import load_dotenv
import os
import aiohttp

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
SECRET_KEY = os.getenv("SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")
conversation_history = {}

@app.route('/')
def home():
    return jsonify({"message": "Flask server is running!"})

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,  # Set to DEBUG for more verbose logs
)
logger = logging.getLogger(__name__)

# Get the bot token and Replicate API token from the environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")

# Ensure tokens are set
if not BOT_TOKEN or not REPLICATE_API_TOKEN:
    raise ValueError("BOT_TOKEN or REPLICATE_API_TOKEN is missing. Check your .env file.")

# Set the token for Replicate
replicate.Client(api_token=REPLICATE_API_TOKEN)

# Telegram bot setup
def start_bot():
    """Start the Telegram bot."""
    # Define functions and handlers as in your original bot code
    # Command to start interaction
    async def start(update: Update, context: CallbackContext) -> None:
        """Handle the /start command."""
        try:
        

            keyboard = [
                [
                    InlineKeyboardButton(
                        text="Open App", web_app={"url": "https://iagent-miniapp-wps8.vercel.app/"}
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Hello! I'm your Injective Agent Bot. How can I assist you today?\nClick the button below to open the web app:",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("An error occurred while processing your request.")

    async def handle_query(update: Update, context: CallbackContext) -> None:
        """Process user queries with context and respond with AI output from the backend server."""
        try:
            user_id = update.message.from_user.id
            user_message = update.message.text  # Get the user's input

            # Initialize or update conversation history for each user
            if user_id not in conversation_history:
                conversation_history[user_id] = []

            # Add the user's message to the conversation history
            conversation_history[user_id].append(f"User: {user_message}")

            # Limit conversation history to the most recent 5 exchanges
            max_history_length = 5
            if len(conversation_history[user_id]) > max_history_length * 2:
                conversation_history[user_id] = conversation_history[user_id][-max_history_length * 2:]

            # Combine conversation history into a single prompt
            conversation_context = "\n".join(conversation_history[user_id])

            # Show typing indicator
            await update.message.chat.send_action("typing")

            # Send the request to your backend to get the response
            backend_url = f"{BASE_URL}/chat"  # Replace with your backend server's URL
            session_id = str(user_id)  # Using user_id as the session_id

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {SECRET_KEY}"  # Replace with your actual secret key
                }
                async with session.post(backend_url, json={
                    "message": user_message,
                    "session_id": session_id,
                    "agent_id": "example-agent",  # Optional, if you need to pass it
                    "agent_key": "ec6d38c60720e5e20f6b0ab989c619652dee84f953250bbf291b3922c8b70656",  # Optional, if you need to pass it
                }, headers=headers) as response:
                    if response.status == 200:
                        # Get the response from your backend
                        response_data = await response.json()
                        ai_response = response_data.get("response", "No response from AI.")
                    else:
                        ai_response = "An error occurred while getting a response from the AI."

            # Log the raw AI response for debugging
            logger.info(f"Raw AI response: {ai_response}")

            # Add AI's response to the conversation history
            conversation_history[user_id].append(f"AI: {ai_response}")

            # Send the AI's response back to the user
            await update.message.reply_text(ai_response)

        except Exception as e:
            logger.error(f"Error handling user query: {e}")
            await update.message.reply_text(f"An error occurred while processing your query. Please try again. error: {e}")

    

    # Create Telegram bot application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    # Run the bot
    application.run_polling()

# Flask and bot threading
if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    flask_thread.daemon = True
    flask_thread.start()

    # Start the Telegram bot
    start_bot()
