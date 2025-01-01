from quart import Quart, jsonify, request
from quart_cors import cors
from database_engine.wallet_model import StorageEngine
import os
from dotenv import load_dotenv
from database_engine.utils.injective_utils import InjectiveTransaction

load_dotenv()



# Quart app initialization
app = Quart(__name__)

# Enable CORS for Quart
#app = cors(app, allow_origin="*", allow_headers=["Authorization", "Content-Type"])

app = cors(
    app,
    
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    allow_methods=["GET", "POST", "OPTIONS"],  # Ensure OPTIONS is included
    allow_origin=["*"],  # Explicitly allow your frontend origin

)
agents = {}

SECRET_KEY = os.getenv("SECRET_KEY")


@app.route("/<path:path>", methods=["OPTIONS"])
async def handle_options(path):
    response = jsonify({"ok": True})
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Authorization, Content-Type")
    return response, 200


@app.before_request
async def authorize():
    if request.method == "OPTIONS" or request.endpoint in ['health_check', 'open_route']:
        return  # Skip auth for OPTIONS and specific routes
        
    """Global middleware to check for Authorization header."""
    # Exclude routes that do not need authorization
    if request.endpoint in ['health_check', 'open_route']:
        return  # Skip auth for these routes

    # Get the Authorization header
    auth_header = request.headers.get('Authorization')

    # Check if the header is present and starts with "Bearer "
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authorization header missing or invalid"}), 401

    # Extract token and validate
    token = auth_header.split("Bearer ")[1]
    if token != SECRET_KEY:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

# Initialize storage engine
storage_engine = StorageEngine()

@app.route('/create_wallet', methods=['POST'])
async def create_wallet():
    try:
        data = await request.get_json()

        if not data:
            return jsonify({"ok": False, "error": "Missing required json body"}), 400

        user_id = data.get("user_id")
        wallet_name = data.get("wallet_name")

        # Call the storage engine method
        result = await storage_engine.create_new_wallet(wallet_name, user_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"ok": False, "message": "Wallet creation failed", "error": str(e)}), 500

@app.route('/add_wallet', methods=['POST'])
async def add_wallet():
    try:
        data = await request.get_json()

        if not data:
            return jsonify({"error": "Missing required json body"}), 400

        user_id = data.get("user_id")
        wallet_name = data.get("wallet_name")

        # Call the storage engine method
        result = await storage_engine.add_wallet(wallet_name, user_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"ok": False, "message": "Wallet creation failed", "error": str(e)}), 500

@app.route('/get_user_details/<user_id>', methods=['GET'])
async def get_user_details(user_id):
    try:
        # Call the storage engine method
        result = await storage_engine.get_user_details(user_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"ok": False, "message": "Error fetching user details", "error": str(e)}), 500
    

async def get_or_create_agent(agent_id, private_key):
    """Retrieve an existing agent or create a new one"""
    if agent_id not in agents:
        agents[agent_id] = await InjectiveTransaction.create(agent_id, private_key)
    return agents[agent_id]


@app.route("/query_balances", methods=["POST"])
async def query_balances():
    """Endpoint to query balances for a given agent"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"ok": False, "error": "user_id is required"}), 400
        
        decrypted_private_key = await storage_engine.get_decrypted_private_key(user_id)

        # Get or create the agent
        agent = await get_or_create_agent(user_id, decrypted_private_key)

        # Call the query_balances method
        balance_response = await agent.query_balances()
        parsed_balances = [
            {
                "token": token,
                "balance": "0" if balance == "The token is not on mainnet!" else balance
            }
            for token, balance in balance_response["result"].items()
        ]

        return jsonify({"ok": True, "balances": parsed_balances}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    

@app.route("/transfer_funds", methods=["POST"])
async def transfer_funds():
    """Endpoint to transfer funds for a given agent"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")
        recipient = data.get("recipient")
        amount = data.get("amount")

        if not user_id  or not recipient or not amount:
            return jsonify({"error": "user_id, recipient, and amount are required"}), 400
        
        decrypted_private_key = await storage_engine.get_decrypted_private_key(user_id)

        # Get or create the agent
        agent = await get_or_create_agent(user_id, decrypted_private_key)

        # Call the transfer_funds method
        result = await agent.transfer_funds(recipient, amount)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/check_user/<user_id>', methods=['GET'])
async def check_user(user_id):
    storage_engine = StorageEngine()
    result = await storage_engine.check_if_user_exists(user_id)
    return jsonify(result)



if __name__ == '__main__':
    app.run(debug=True)
