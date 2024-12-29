from quart import Quart, jsonify
from mongoengine import Document, StringField, ListField, EmbeddedDocumentField, EmbeddedDocument, connect
from database_engine.utils.create_wallet import create_injective_wallet
from database_engine.utils.encrypt import encrypt
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_NAME = os.environ.get('DATABASE_NAME')


class WalletItem(EmbeddedDocument):
    wallet_name = StringField(required=True)
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
    def __init__(self, host=DATABASE_URL):
        connect(db=DB_NAME, host=host)

    async def create_new_wallet(self, wallet_name, user_id):
        """
        Create a new wallet for a user.
        """
        try:
            if not wallet_name:
                return jsonify({"error": "wallet_name is missing"}), 400

            # Create a new Injective wallet
            wallet_data = create_injective_wallet()
            if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
                return jsonify({"error": "Wallet creation failed"}), 500

            # Encrypt the private key
            encrypted_private_key = encrypt(wallet_data['privateKey'])

            # Create and save wallet document
            wallet = Wallet(
                user_id=user_id,
                current_injective_address=wallet_data['injectiveAddress'],
                wallets=[
                    WalletItem(
                        wallet_name=wallet_name,
                        injective_address=wallet_data['injectiveAddress'],
                        evm_address=wallet_data['evmAddress'],
                        private_key=encrypted_private_key
                    )
                ]
            )
            wallet.save()  # Save asynchronously

            return jsonify({
                "ok": True,
                "user_id": user_id,
                "wallet_name": wallet_name,
                "injective_address": wallet_data['injectiveAddress'],
                "evm_address": wallet_data['evmAddress'],
            })

        except Exception as e:
            print("Error creating wallet:", str(e))
            return jsonify({"ok": False, "error": "Error adding new wallet"}), 500

        


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
            user_wallets = Wallet.objects(user_id=user_id).first()  # Async query
            if not user_wallets:
                return jsonify({"error": "User not found"}), 404
            
            
            # Check if wallet with the same name already exists for the user
            for wallet in user_wallets.wallets:
                if wallet.wallet_name == wallet_name:
                    return jsonify({"error": f"Wallet name '{wallet_name}' already exists for this user"}), 400

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
            user_wallets.update(push__wallets=new_wallet)

            # Fetch updated user
            updated_user = Wallet.objects(user_id=user_id).first()

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


