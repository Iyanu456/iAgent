from quart import Quart, jsonify
from mongoengine import Document, StringField, ListField, EmbeddedDocumentField, EmbeddedDocument, connect
from utils.create_wallet import create_injective_wallet
from utils.encrypt import encrypt
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_NAME = os.environ.get('DATABASE_NAME')


class WalletItem(EmbeddedDocument):
    wallet_name = StringField(required=True, unique=True)
    injective_address = StringField(required=True, unique=True)
    evm_address = StringField(required=True, unique=True)
    private_key = StringField(required=True)  # Encrypted private key


class Wallet(Document):
    user_id = StringField(required=True, unique=True)  # Unique user ID
    current_injective_address = StringField(unique=True)
    wallets = ListField(EmbeddedDocumentField(WalletItem))  # List of wallet items

    meta = {
        'collection': 'wallets',  # Optional: Specify collection name
        'indexes': [
            {'fields': ['user_id'], 'unique': True},  # Ensure user_id is unique
            {'fields': ['current_injective_address'], 'unique': True}
        ]
    }


class StorageEngine:
    def __init__(self, db_name, host=DATABASE_URL):
        connect(db=DB_NAME, host=host)

    async def create_user(self, user_id):
        try:
            # Create a new user and save to DB
            user = Wallet(user_id=user_id)
            await user.save()  # Using await here as we want to make it async
            return jsonify({
                "ok": True,
                "message": "User created successfully"
            })

        except Exception as e:
            print("Error creating user:", str(e))
            return jsonify({
                "ok": False,
                "error": "User creation failed"
            }), 500


    async def add_wallet(self, wallet_name, user_id):
        """
        Add a new wallet to an existing user.
        """
        try:
            if not user_id:
                return jsonify({"error": "User ID is required"}), 400

            if not wallet_name:
                return jsonify({"error": "Wallet name is required"}), 400

            # Fetch the user document
            user_wallets = await Wallet.objects(user_id=user_id).first()  # Async query
            if not user_wallets:
                return jsonify({"error": "User not found"}), 404

            # Create a new Injective wallet
            wallet_data = create_injective_wallet()
            if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
                return jsonify({"error": "Wallet creation failed"}), 500

            # Encrypt the private key
            encrypted_private_key = encrypt(wallet_data['privateKey'])

            # Create new wallet item
            new_wallet = WalletItem(
                wallet_name=wallet_name,
                injective_address=wallet_data['injectiveAddress'],
                evm_address=wallet_data['evmAddress'],
                private_key=encrypted_private_key
            )

            # Update the user's wallets list
            await user_wallets.update(push__wallets=new_wallet)

            # Fetch updated user
            updated_user = await Wallet.objects(user_id=user_id).first()

            return jsonify({
                "ok": True,
                "user_id": updated_user.user_id,
                "new_wallet": {
                    "wallet_name": wallet_name,
                    "injective_address": wallet_data['injectiveAddress'],
                    "evm_address": wallet_data['evmAddress'],
                },
                "wallets": [{
                    "wallet_name": wallet.wallet_name,
                    "injective_address": wallet.injective_address,
                    "evm_address": wallet.evm_address,
                } for wallet in updated_user.wallets],
            })

        except Exception as e:
            print("Error adding wallet:", str(e))
            return jsonify({"ok": False, "error": "Error adding new wallet"}), 500

    async def get_user_details(self, user_id):
        """
        Fetch user details by user ID.
        """
        try:
            # Fetch user document
            user = await Wallet.objects(user_id=user_id).first()  # Async query
            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify({
                "ok": True,
                "user_id": user.user_id,
                "wallets": [{
                    "wallet_name": wallet.wallet_name,
                    "injective_address": wallet.injective_address,
                    "evm_address": wallet.evm_address,
                } for wallet in user.wallets],
            })

        except Exception as e:
            print("Error fetching user details:", str(e))
            return jsonify({"ok": False, "error": "Error fetching user's details"}), 500


# Quart app initialization
app = Quart(__name__)

# Initialize storage engine
storage_engine = StorageEngine(db_name="wallet_db")

@app.route('/create_user/<user_id>', methods=['POST'])
async def create_user(user_id):
    return await storage_engine.create_user(user_id)

@app.route('/create_wallet/<user_id>/<wallet_name>', methods=['POST'])
async def create_wallet(user_id, wallet_name):
    return await storage_engine.create_new_wallet(wallet_name, user_id)

@app.route('/add_wallet/<user_id>/<wallet_name>', methods=['POST'])
async def add_wallet(user_id, wallet_name):
    return await storage_engine.add_wallet(wallet_name, user_id)

@app.route('/get_user_details/<user_id>', methods=['GET'])
async def get_user_details(user_id):
    return await storage_engine.get_user_details(user_id)

if __name__ == '__main__':
    app.run(debug=True)
