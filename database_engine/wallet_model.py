from quart import jsonify
from mongoengine import Document, StringField, ListField, EmbeddedDocumentField, EmbeddedDocument, connect
from database_engine.utils.create_wallet import create_injective_wallet
from database_engine.utils.encrypt import encrypt
from database_engine.utils.decrypt import decrypt
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
        self.agents= {}
        connect(db=DB_NAME, host=host)

    async def create_new_wallet(self, wallet_name, user_id):
        """
        Create a new wallet for a user.
        """
        try:
            if not wallet_name:
                return ({"ok": False, "error": "wallet_name is missing"})

            # Create a new Injective wallet
            wallet_data = create_injective_wallet()
            if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
                return ({"ok":False,"error": "Wallet creation failed"})

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

            return ({
                "ok": True,
                "user_id": user_id,
                "wallet_name": wallet_name,
                "injective_address": wallet_data['injectiveAddress'],
                "evm_address": wallet_data['evmAddress'],
            })

        except Exception as e:
            print("Error creating wallet:", str(e))
            return ({"ok": False, "error": "Error adding new wallet"})

        


    async def add_wallet(self, wallet_name, user_id):
        """
        Add a new wallet to an existing user.
        """
        try:
            if not user_id:
                return ({"ok": False, "error": "User ID is required"})

            if not wallet_name:
                return ({"ok": False, "error": "Wallet name is required"})
            

            # Fetch the user document
            user_wallets = Wallet.objects(user_id=user_id).first()  # Async query
            if not user_wallets:
                return ({"ok": False, "error": "User not found"})
            
            
            # Check if wallet with the same name already exists for the user
            for wallet in user_wallets.wallets:
                if wallet.wallet_name == wallet_name:
                    return ({"ok": False, "error": f"Wallet name '{wallet_name}' already exists for this user"})

            # Create a new Injective wallet
            wallet_data = create_injective_wallet()
            if not wallet_data['privateKey'] or not wallet_data['injectiveAddress']:
                return ({"ok": False, "error": "Wallet creation failed"})

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

            return ({
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
                return ({"ok": False, "error": "User not found"})

            return ({
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
            return ({"ok": False, "error": "Error fetching user's details"})
        
    async def get_decrypted_private_key(self, user_id):
        """
        Get the decrypted private key for the user's current Injective address.
        """
        try:
            # Fetch the user document
            user = Wallet.objects(user_id=user_id).first()
            if not user:
                return {"ok": False, "error": "User not found"}
            
            # Get the current Injective address
            current_address = user.current_injective_address
            if not current_address:
                return {"ok": False, "error": "Current Injective address not set"}

            # Find the wallet associated with the current Injective address
            wallet_item = next(
                (wallet for wallet in user.wallets if wallet.injective_address == current_address), 
                None
            )
            if not wallet_item:
                return {"ok": False, "error": "No wallet found for the current Injective address"}

            # Decrypt the private key
            decrypted_private_key = decrypt(wallet_item.private_key)

            if decrypted_private_key.startswith("0x"):
                decrypted_private_key = decrypted_private_key[2:]
            
            return (decrypted_private_key)

        except Exception as e:
            print("Error getting decrypted private key:", str(e))
            return {"ok": False, "error": "Error retrieving decrypted private key"}


    async def check_if_user_exists(self, user_id):
        """
        Check if a user exists in the database.
        """
        try:
            # Fetch user document
            user = Wallet.objects(user_id=user_id).first()  # Sync query for simplicity
            if user:
                return {"ok": True, "exists": True, "message": "User exists."}
            else:
                return {"ok": True, "exists": False, "message": "User does not exist."}
        except Exception as e:
            print("Error checking if user exists:", str(e))
            return {"ok": False, "error": "Error checking user existence."}
        

