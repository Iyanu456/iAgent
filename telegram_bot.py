from keep_alive import keep_alive
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ChatInviteLink
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
from database_engine.wallet_model import StorageEngine

from database_engine.utils.injective_utils import InjectiveTransaction

storage_engine = StorageEngine()

#print (user)

#keep_alive()
# Load environment variables from .env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

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
if not REPLICATE_API_TOKEN:
    raise ValueError("Replicate API token is missing. Set REPLICATE_API_TOKEN in your environment.")

# Set the token for Replicate
replicate.Client(api_token=REPLICATE_API_TOKEN)

# Global conversation history dictionary
conversation_history = {}
agents= {}

if not BOT_TOKEN:
    logger.critical("Bot token is missing. Please set BOT_TOKEN in your .env file.")
    exit(1)

async def get_or_create_agent(agent_id, private_key):
    """Retrieve an existing agent or create a new one"""
    if agent_id not in agents:
        agents[agent_id] = await InjectiveTransaction.create(agent_id, private_key)
    return agents[agent_id]

# Define your functions that return actual values (e.g., get_current_price, get_balance)
def get_current_price():
    # Placeholder function that returns current price
    return ("The current price of the INJ token is $33.5")  # Example return value

def get_balance():
    # Placeholder function that returns balance
    return 1500  # Example return value

# Mapping of placeholders to functions
placeholder_functions = {
    "get_current_price()": get_current_price,
    "get_balance()": get_balance,
    # Add more placeholders and their corresponding functions here
}

def replace_placeholders(response: str) -> str:
    """Replace function placeholders in the response with actual function outputs."""
    has_placeholder = any(placeholder in response for placeholder in placeholder_functions)
    
    if has_placeholder:
        for placeholder, func in placeholder_functions.items():
            if placeholder in response:
                # Call the corresponding function and replace the placeholder with its return value
                actual_value = func()
                response = response.replace(placeholder, str(actual_value))
    else:
        logger.info("No placeholders found in response.")
    
    return response

# Command to start interaction
async def start(update: Update, context: CallbackContext) -> None:

    user_id = update.effective_user.id  # Telegram User ID
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    await storage_engine.create_new_wallet("wallet", f"{user_id}")
    """Handle the /start command."""
    try:
        

        keyboard = [
            [
                InlineKeyboardButton(
                    text="Open App", web_app={"url": f"https://iagent-miniapp-wps8.vercel.app/{user_id}"}
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Hello! {username} I'm your Injective Agent Bot. How can I assist you today?\nClick the button below to open the web app",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("An error occurred while processing your request.")


# Command to handle /transfer
async def transfer(update: Update, context: CallbackContext) -> None:
    """Handle the /transfer command."""
    try:
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Transfer funds", web_app={"url": "https://iagent-miniapp-wps8.vercel.app/"}
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Click the button below to transfer your funds \n\n\n",
            
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error in transfer command: {e}")
        await update.message.reply_text("An error occurred while processing your request.")


# Command to handle /balance
async def balance(update: Update, context: CallbackContext) -> None:
    """Handle the /balance command to fetch the INJ balance."""
    try:
        user_id = str(update.message.from_user.id)  # Get the user_id of the person sending the command

        # Get the decrypted private key for the user
        decrypted_private_key = await storage_engine.get_decrypted_private_key(user_id)

        # Get or create the agent for the user
        agent = await get_or_create_agent(user_id, decrypted_private_key)

        # Query balances using the agent
        balance_response = await agent.query_balances()

        # Extract the balance for the 'inj' token
        parsed_balances = [
            {
                "token": token,
                "balance": "0" if balance == "The token is not on mainnet!" else balance
            }
            for token, balance in balance_response["result"].items()
        ]

        # Get the balance for 'inj'
        inj_balance = next((item["balance"] for item in parsed_balances if item["token"] == "inj"), "0")

        # Send the balance to the user
        await update.message.reply_text(f"Your INJ balance is: {inj_balance}")

    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await update.message.reply_text(f"An error occurred while processing your request. {e}")



# Help command to show available commands
async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    try:
        await update.message.reply_text("Available commands:\n/start - Start interacting\n/help - Get help\n/balance - Check INJ balance\n/transfer - Transfer funds")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("An error occurred while processing your request.")

# Global error handler
async def error_handler(update: object, context: CallbackContext) -> None:
    """Handle unexpected errors."""
    logger.error("An unexpected error occurred", exc_info=context.error)
    try:
        if update and update.message:
            await update.message.reply_text("An unexpected error occurred. Please try again later.")
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)

# Handle user queries and AI responses
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
                "message": f" {user_message}",
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


# Main function to run the bot
def main():
    """Start the bot."""
    try:
        # Create the Application instance with your bot token
        application = Application.builder().token(BOT_TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("transfer", transfer))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("help", help_command))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

        # Register the global error handler
        application.add_error_handler(error_handler)

        # Start the bot
        application.run_polling()
        print("Bot started and running!")

    except Exception as e:
        logger.critical(f"Critical failure in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
