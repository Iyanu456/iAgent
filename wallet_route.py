from flask import Flask, request, jsonify, current_app, g
from motor.motor_asyncio import AsyncIOMotorClient
import os
from utils.create_wallet import create_injective_wallet
from utils.encrypt import encrypt
import asyncio
from dotenv import load_dotenv
from hypercorn.config import Config
from hypercorn.asyncio import serve
import pymongo
from werkzeug.local import LocalProxy

load_dotenv()

#DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
# Flask setup
app = Flask(__name__)

# MongoDB setup
MONGO_URI = os.getenv('DATABASE_URL')
"""client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]  # Replace with your database name
wallets_collection = db['wallets']"""

if not MONGO_URI:
            raise ValueError(
                "MONGO_URI is required"
            )
if not DATABASE_NAME:
            raise ValueError(
                "DATABASE_NAME is required"
            )

client = None
wallets_collection = None  # Define globally

async def connect_to_db():
    """Establish a connection to the MongoDB server."""
    global client, wallets_collection
    if client is None:
        try:
            client = AsyncIOMotorClient(MONGO_URI)
            print("Connected to MongoDB.")
            db = client[DATABASE_NAME]
            wallets_collection = db['wallets']
            print(f"Initialized collection: {wallets_collection.name}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {str(e)}")
            raise e

async def close_db_connection():
    """Close the MongoDB connection."""
    global client
    if client is not None:
        client.close()
        print("MongoDB connection closed.")

# Endpoint: Create New Wallet
@app.route('/wallet', methods=['POST'])
async def create_wallet():
    try:
        data = request.json
        user_id = data.get('userId')

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        wallet_name = 'wallet'
        wallet_data = create_injective_wallet()
        print(wallet_data)  # Check the structure of the data here


        if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
            return jsonify({"error": "Wallet creation failed"}), 500

        # Encrypt the private key
        encrypted_private_key = encrypt(wallet_data['privateKey'])

        # Check for duplicate Injective address
        existing_wallet = wallets_collection.find_one(
            {"current_injective_address": wallet_data['injectiveAddress']}
        )
        if existing_wallet:
            return jsonify({"error": "Wallet with this Injective address already exists"}), 400

        # Save wallet details to the database
        wallet_document = {
            "userId": user_id,
            "current_injective_address": wallet_data['injectiveAddress'],
            "wallets": [
                {
                    "wallet_name": wallet_name,
                    "injective_address": wallet_data['injectiveAddress'],
                    "evm_address": wallet_data['evmAddress'],
                    "private_key": encrypted_private_key,
                }
            ]
        }
        await wallets_collection.insert_one(wallet_document)

        return jsonify({
            "ok": True,
            "userId": user_id,
            "wallet_name": wallet_name,
            "injective_address": wallet_data['injectiveAddress'],
            "evm_address": wallet_data['evmAddress'],
        })
    except Exception as e:
        print("Error creating wallet:", str(e))
        return jsonify({"error": "Failed to create wallet"}), 500

# Endpoint: Add a New Wallet to an Existing User
@app.route('/wallet/add', methods=['POST'])
async def add_wallet():
    try:
        data = request.json
        user_id = data.get('userId')
        wallet_name = data.get('wallet_name')

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        if not wallet_name:
            return jsonify({"error": "Wallet name is required"}), 400

        # Find user by userId
        user_wallets = wallets_collection.find_one({"userId": user_id})

        if not user_wallets:
            return jsonify({"error": "User not found"}), 404

        # Check if the wallet name already exists
        if any(wallet['wallet_name'] == wallet_name for wallet in user_wallets['wallets']):
            return jsonify({"error": "Wallet name already exists"}), 400

        # Generate a new wallet
        wallet_data = create_injective_wallet()
        if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
            return jsonify({"error": "Wallet creation failed"}), 500

        # Encrypt the private key
        encrypted_private_key = encrypt(wallet_data['privateKey'])

        # Add new wallet to the user's wallets array
        new_wallet = {
            "wallet_name": wallet_name,
            "injective_address": wallet_data['injectiveAddress'],
            "evm_address": wallet_data['evmAddress'],
            "private_key": encrypted_private_key,
            "balance": 0,
        }
        await wallets_collection.update_one(
            {"userId": user_id},
            {"$push": {"wallets": new_wallet}}
        )

        # Respond with the updated user data
        updated_user = await wallets_collection.find_one({"userId": user_id})
        return jsonify({
            "ok": True,
            "userId": updated_user['userId'],
            "newWallet": {
                "wallet_name": wallet_name,
                "injective_address": wallet_data['injectiveAddress'],
                "evm_address": wallet_data['evmAddress'],
            },
            "wallets": [
                {
                    "wallet_name": wallet['wallet_name'],
                    "injective_address": wallet['injective_address'],
                    "evm_address": wallet['evm_address'],
                    "balance": wallet['balance'],
                }
                for wallet in updated_user['wallets']
            ],
        })
    except Exception as e:
        print("Error adding wallet:", str(e))
        return jsonify({"error": "Failed to add wallet"}), 500
    


async def app_startup():
    """Run tasks needed at app startup."""
    await connect_to_db()


async def app_shutdown():
    """Run tasks needed at app shutdown."""
    await close_db_connection()


async def main_async():
    """Main application logic."""
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await app_startup()
    try:
        await serve(app, config)
    finally:
        await app_shutdown()


if __name__ == "__main__":
    # Run the main_async function using the default asyncio loop
    try:
        asyncio.run(main_async())
    except Exception as e:
        print(f"Error during application startup: {str(e)}")