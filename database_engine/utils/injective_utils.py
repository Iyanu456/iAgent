import os
import asyncio
from dotenv import load_dotenv
from injective_functions.factory import InjectiveClientFactory
from injective_functions.utils.function_helper import (
    FunctionExecutor,
)

# Load environment variables
load_dotenv()
ENVIRONMENT = os.getenv("ENVIRONMENT", "mainnet")



class InjectiveChainClient:
    def __init__(self):
        self.agents = {}
        self.bank_client = None

    async def initialize_agent(self, agent_id: str, private_key: str, environment: str = "mainnet") -> None:
        """Initialize Injective clients if they don't exist"""
        if agent_id not in self.agents:
            clients = await InjectiveClientFactory.create_all(
                private_key=private_key, network_type=environment
            )
            self.agents[agent_id] = clients

    async def execute_function(self, function_name: str, arguments: dict, agent_id: str) -> dict:
        """Execute the appropriate Injective function with error handling"""
        try:
            # Get the client dictionary for this agent
            clients = self.agents.get(agent_id)
            if not clients:
                return {
                    "error": "Agent not initialized. Please provide valid credentials."
                }

            return await FunctionExecutor.execute_function(
                clients=clients, function_name=function_name, arguments=arguments
            )
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "details": {"function": function_name, "arguments": arguments},
            }


class InjectiveTransaction:
    def __init__(self, agent_id, private_key, chain_client):
        self.agent_id = agent_id
        self.private_key = private_key
        self.chain_client = chain_client

    @classmethod
    async def create(cls, agent_id, private_key):
        """Asynchronous factory method to initialize InjectiveTransaction"""
        chain_client = InjectiveChainClient()
        await chain_client.initialize_agent(agent_id, private_key, ENVIRONMENT)
        return cls(agent_id, private_key, chain_client)

    async def query_balances(self):
        arguments = {
            "denom_list": ["inj", "usdt", "eth"],
        }
        try:
            result = await self.chain_client.execute_function(
                function_name="query_balances",
                arguments=arguments,
                agent_id=self.agent_id,
            )
            #print(result)
            return result
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {"ok": False, "message": f"Error fetching balance: {e}"}

    async def transfer_funds(self, recipient, amount):
        arguments = {
            "to_address": f"{recipient}",
            "amount": f"{amount}",
            "denom": "INJ",
        }
        try:
            result = await self.chain_client.execute_function(
                function_name="transfer_funds",
                arguments=arguments,
                agent_id=self.agent_id,
            )
            #print(result)
            return result
        except Exception as e:
            print(f"Error transferring funds: {e}")
            return {"ok": False, "message": f"Error transferring funds: {e}"}


"""async def main():
    # Initialize the agent
    agent_id = "your_agent_id"
    private_key = "ec6d38c60720e5e20f6b0ab989c619652dee84f953250bbf291b3922c8b70656"

    # Use the asynchronous create method to initialize
    utils = await InjectiveTransaction.create(agent_id, private_key)

    # Test query_balances
    balances = await utils.query_balances()
    print("Balances:", balances)

    # Test transfer_funds
    recipient = "inj1aj5w58z2kpyx3g4yj7f2ynx3zgr4qykuces0m3"
    amount = "0.2"
    transfer_result = await utils.transfer_funds(recipient, amount)
    print("Transfer Result:", transfer_result)

    balances = await utils.query_balances()
    print("Balances:", balances)"""
"""

if __name__ == "__main__":
    asyncio.run(main())"""
