import os
from dotenv import load_dotenv
from injective_functions.bank import InjectiveBank
from injective_functions.utils.indexer_requests import fetch_decimal_denoms
from injective_functions.utils.helpers import detailed_exception_info
from injective_functions.factory import InjectiveClientFactory
from injective_functions.utils.function_helper import (
    FunctionSchemaLoader,
    FunctionExecutor,
)

class InjectiveChainClient:
    def __init__(self):
        load_dotenv()
        self.agents = {}
        self.bank_client = None

    """async def initialize_agent(
            self, agent_id: str, private_key: str, environment: str = "mainnet") -> None:
        if agent_id not in self.agents:
            clients = await InjectiveClientFactory.create_all(
                private_key=private_key, network_type=environment
            )
            self.agents[agent_id] = clients
            self.bank_client = InjectiveBank(chain_client=clients)  # Initialize InjectiveBank
            print(f"Agent {agent_id} initialized for environment {environment}.")"""

    async def initialize_agent(
        self, agent_id: str, private_key: str, environment: str = "mainnet"
    ) -> None:
        """Initialize Injective clients if they don't exist"""
        if agent_id not in self.agents:
            clients = await InjectiveClientFactory.create_all(
                private_key=private_key, network_type=environment
            )
            self.agents[agent_id] = clients

    
    async def execute_function(
        self, function_name: str, arguments: dict, agent_id: str
    ) -> dict:
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

    def get_bank_client(self):
        """Retrieve the initialized bank client."""
        return self.bank_client



import asyncio

async def test_chain_client():
    private_key = "ec6d38c60720e5e20f6b0ab989c619652dee84f953250bbf291b3922c8b70656"
    agent_id = "example-agent"
    environment = "mainnet"

    chain_client = InjectiveChainClient()
    await chain_client.initialize_agent(agent_id, private_key, environment)

    bank_client = chain_client.get_bank_client()
    if bank_client:
        print(f"Bank client successfully initialized.")

        # Replace with a valid Injective address
        address = "inj1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        try:
            balance_2 = await chain_client.execute_function("query_balances", {}, )
            balance = await bank_client.query_balances(client_address=address)
            print(f"Balance for address {address}: {balance}")
        except Exception as e:
            print(f"Error fetching balance: {e}")
    else:
        print(f"Failed to initialize bank client.")



# Example of running query_balances using the execute_function

import asyncio

async def main():
    # Create an instance of your InjectiveChainClient
    client = InjectiveChainClient()
    
    # Initialize an agent
    private_key = "ec6d38c60720e5e20f6b0ab989c619652dee84f953250bbf291b3922c8b70656"
    agent_id = "example-agent"
    environment = "testnet"
    address = "inj1rrqc20lhy48e9lxetcpxvqwj3t594hwy3q3y77"
    
    await client.initialize_agent(agent_id=agent_id, private_key=private_key, environment=environment)
    
    # Arguments for the query_balances function
    arguments = {
        "denom_list": ["inj", "usdt", "eth"],
        #"client_address": address  # List of token denominations to query. Can be empty to fetch all balances.
    }
    
    # Execute the query_balances function
    result = await client.execute_function(
        function_name="query_balances",
        arguments=arguments,
        agent_id=agent_id
    )
    
    # Print the result
    if "error" in result:
        print("Error:", result["error"])
    else:
        print("Balances:", result)



async def transfer():
    # Create an instance of your InjectiveChainClient
    client = InjectiveChainClient()
    
    # Initialize an agent
    private_key = "ec6d38c60720e5e20f6b0ab989c619652dee84f953250bbf291b3922c8b70656"
    agent_id = "example-agent"
    environment = "testnet"
    address = "inj1rrqc20lhy48e9lxetcpxvqwj3t594hwy3q3y77"
    
    await client.initialize_agent(agent_id=agent_id, private_key=private_key, environment=environment)
    
    # Arguments for the query_balances function
    arguments = {
        "to_address": "inj1aj5w58z2kpyx3g4yj7f2ynx3zgr4qykuces0m3",
        "amount": "0.000000012",
        
        "denom": "INJ",
        #"client_address": address  # List of token denominations to query. Can be empty to fetch all balances.
    }
    
    # Execute the query_balances function
    result = await client.execute_function(
        function_name="transfer_funds",
        arguments=arguments,
        agent_id=agent_id
    )
    
    # Print the result
    if "error" in result:
        print("Error:", result["error"])
    else:
        print("Balances:", result)
# Run the script
if __name__ == "__main__":
    asyncio.run(transfer())



"""if __name__ == "__main__":
    asyncio.run(test_chain_client())"""
