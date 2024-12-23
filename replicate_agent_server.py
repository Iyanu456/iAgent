import os
import requests
from dotenv import load_dotenv
from quart import Quart, request, jsonify
from datetime import datetime
import argparse
from injective_functions.factory import InjectiveClientFactory
from injective_functions.utils.function_helper import (
    FunctionSchemaLoader,
    FunctionExecutor,
)
import json
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve
import aiohttp





import replicate


# Set up the Replicate client
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise ValueError("Replicate API token is missing. Set REPLICATE_API_TOKEN in your environment.")
replicate.Client(api_token=REPLICATE_API_TOKEN)


# Initialize Quart app (async version of Flask)
app = Quart(__name__)

class InjectiveChatAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Get Replicate API key from environment variable
        self.replicate_api_key = os.getenv("REPLICATE_API_KEY")
        if not self.replicate_api_key:
            raise ValueError(
                "No Replicate API key found. Please set the REPLICATE_API_KEY environment variable."
            )

        # Initialize conversation histories
        self.conversations = {}
        # Initialize injective agents
        self.agents = {}
        schema_paths = [
            "./injective_functions/account/account_schema.json",
            "./injective_functions/auction/auction_schema.json",
            "./injective_functions/authz/authz_schema.json",
            "./injective_functions/bank/bank_schema.json",
            "./injective_functions/exchange/exchange_schema.json",
            "./injective_functions/staking/staking_schema.json",
            "./injective_functions/token_factory/token_factory_schema.json",
            "./injective_functions/utils/utils_schema.json",
        ]
        self.function_schemas = FunctionSchemaLoader.load_schemas(schema_paths)

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

   # Function to interact with Replicate for the model response
async def get_response_from_replicate(prompt: str) -> str:
    """Get a response from Replicate's Llama model using the provided prompt."""
    try:
        response = ""
        for event in replicate.stream(
            "meta/llama-2-7b-chat",  # Model version
            input={
                "top_k": 0,
                "top_p": 1,
                "prompt": prompt,
                "max_tokens": 512,
                "temperature": 0.75,
                "system_prompt": (
                    "You are a helpful AI assistant on Injective Chain. "
                    "For questions about INJ price, respond with 'get_current_price()'. "
                    "For other queries, provide appropriate answers based on user input."
                ),
                "length_penalty": 1,
                "max_new_tokens": 800,
                "prompt_template": "<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{prompt} [/INST]",
                "presence_penalty": 0,
                "log_performance_metrics": False
            },
        ):
            response += str(event)

        return response
    except Exception as e:
        # Handle any errors that may arise when calling Replicate's API
        print(f"Error during Replicate API call: {e}")
        return "Sorry, I couldn't process your request at the moment."

# Example usage in your backend route
@app.route('/query', methods=['POST'])
async def query():
    """Handle a query from the user."""
    data = await request.get_json()
    user_message = data.get("message")

    # Conversation context (history and user input)
    prompt = f"User: {user_message}\nAI:"
    
    # Call the Replicate API for response
    ai_response = await get_response_from_replicate(prompt)
    
    # Return the response to the client
    return jsonify({"response": ai_response})

    def clear_history(self, session_id="default"):
        """Clear conversation history for a specific session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id="default"):
        """Get conversation history for a specific session."""
        return self.conversations.get(session_id, [])


# Initialize chat agent
agent = InjectiveChatAgent()


@app.route("/ping", methods=["GET"])
async def ping():
    """Health check endpoint"""
    return jsonify(
        {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
    )


@app.route("/chat", methods=["POST"])
async def chat_endpoint():
    """Main chat endpoint"""
    data = await request.get_json()
    try:
        if not data or "message" not in data:
            return (
                jsonify(
                    {
                        "error": "No message provided",
                        "response": "Please provide a message to continue our conversation.",
                        "session_id": data.get("session_id", "default"),
                        "agent_id": data.get("agent_id", "default"),
                        "agent_key": data.get("agent_key", "default"),
                        "environment": data.get("environment", "testnet"),
                    }
                ),
                400,
            )

        session_id = data.get("session_id", "default")
        private_key = data.get("agent_key", "default")
        agent_id = data.get("agent_id", "default")
        response = await agent.get_response(
            data["message"], session_id, private_key, agent_id
        )

        return jsonify(response)
    except Exception as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "response": "I apologize, but I encountered an error. Please try again.",
                    "session_id": data.get("session_id", "default"),
                }
            ),
            500,
        )


@app.route("/history", methods=["GET"])
async def history_endpoint():
    """Get chat history endpoint"""
    session_id = request.args.get("session_id", "default")
    return jsonify({"history": agent.get_history(session_id)})


@app.route("/clear", methods=["POST"])
async def clear_endpoint():
    """Clear conversation history endpoint"""
    data = await request.get_json()
    session_id = data.get("session_id", "default")
    agent.clear_history(session_id)
    return jsonify({"status": "history cleared", "session_id": session_id})


# Run Quart app with Hypercorn
if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    asyncio.run(serve(app, config))
