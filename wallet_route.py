from quart import Quart
from database_engine.wallet_model import StorageEngine

# Quart app initialization
app = Quart(__name__)

# Initialize storage engine
storage_engine = StorageEngine()

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
