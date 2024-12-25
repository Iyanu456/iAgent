#from openai import OpenAI
import replicate
from quart_cors import cors
import os
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

# Initialize Quart app (async version of Flask)
app = Quart(__name__)
app = cors(app, allow_origin="*")  

SECRET_KEY = os.getenv("SECRET_KEY")




class InjectiveChatAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Get API key from environment variable
        self.api_key = os.getenv("REPLICATE_API_TOKEN")
        if not self.api_key:
            raise ValueError(
                "No REPLICATE API key found. Please set the OPENAI_API_KEY environment variable."
            )

        # Initialize OpenAI client
        self.client = replicate.Client(api_token=self.api_key)

        # Initialize conversation histories
        self.conversations = {}
        # Initialize injective agents
        self.agents = {}
        #schema_paths = [
        #    "./injective_functions/account/account_schema.json",
        #    "./injective_functions/auction/auction_schema.json",
        #    "./injective_functions/authz/authz_schema.json",
        #    "./injective_functions/bank/bank_schema.json",
        #    "./injective_functions/exchange/exchange_schema.json",
        #    "./injective_functions/staking/staking_schema.json",
        #    "./injective_functions/token_factory/token_factory_schema.json",
        #    "./injective_functions/utils/utils_schema.json",
        #]
        #self.function_schemas = FunctionSchemaLoader.load_schemas(schema_paths)

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

    async def get_response(
        self,
        message,
        session_id="default",
        private_key=None,
        agent_id=None,
        environment="mainnet",
    ):
        """Get response from REPLICATE API."""
        await self.initialize_agent(
            agent_id=agent_id, private_key=private_key, environment=environment
        )
        print("initialized agents")
        try:
            # Initialize conversation history for new sessions
            if session_id not in self.conversations:
                self.conversations[session_id] = []

            # Add user message to conversation history
            #self.conversations[session_id].append({"role": "user", "content": message})

            # Add the user's message to the conversation history
            self.conversations[session_id].append({"role": "user", "content": message})

           # Build the conversation context in the desired format
            conversation_context = "\n".join(
                [f'{item["role"]}: {item["content"]}' for item in self.conversations[session_id]]
            )

            # Prepare the prompt for the AI
            prompt = f"{conversation_context}\nAI:"

            # Assume `ai_response` is generated here
            ai_response = "This is the AI's response."  # Replace with actual AI generation logic

            # Append the AI's response
            self.conversations[session_id].append({"role": "AI", "content": ai_response})

            # Get response from OpenAI
            
            # Call the Replicate API with the updated prompt
            response = ""
            for event in replicate.stream(
                "meta/llama-2-7b-chat",
                input={
                    "top_k": 0,
                    "top_p": 1,
                    "prompt": prompt,
                    "max_tokens": 512,
                    "temperature": 0.75,
                    "system_prompt": (
                    """role: system"
                    user's address: inj1rrqc20lhy48e9lxetcpxvqwj3t594hwy3q3y77
                    content": You are a helpful AI assistant on Injective Chain. 
                    You will be answering all things related to Injective Chain and assist with
                    on-chain functions.

                    don't make unnecessary responses about balance checking, making tranfers and the likes unless explicitly asked to

                     When users want to check their balance,  respond only with the text `function query_balance(<user's address>)`'
                     When users want to make transfers,  respond only with the text `function transfer_funds(<amount to transfer (do not add currency or token here)>, <address to transfer to>, <currency or token>)`'
                    
                     
                   """

                    ),
                    "length_penalty": 1,
                    "max_new_tokens": 800,
                    "prompt_template": "<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{prompt} [/INST]",
                    "presence_penalty": 0,
                    "log_performance_metrics": False
                },
            ):
                response += str(event)

            response_message = response

            #print(response_message)
            # Handle function calling
            """if (
                hasattr(response_message, "function_call")
                and response_message.function_call
            ):
                # Extract function details
                function_name = response_message.function_call.name
                function_args = json.loads(response_message.function_call.arguments)
                # Execute the function
                function_response = await self.execute_function(
                    function_name, function_args, agent_id
                )

                # Add function call and response to conversation
                self.conversations[session_id].append(
                    {
                        "role": "assistant",
                        "content": None,
                        "function_call": {
                            "name": function_name,
                            "arguments": json.dumps(function_args),
                        },
                    }
                )

                self.conversations[session_id].append(
                    {
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    }
                )

                # Get final response
                second_response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4-turbo-preview",
                    messages=self.conversations[session_id],
                    max_tokens=2000,
                    temperature=0.7,
                )

                final_response = second_response.choices[0].message.content.strip()
                self.conversations[session_id].append(
                    {"role": "assistant", "content": final_response}
                )

                return {
                    "response": final_response,
                    "function_call": {
                        "name": function_name,
                        "result": function_response,
                    },
                    "session_id": session_id,
                }
            """
            # Handle regular response
            #bot_message = response_message.content
            if response:
                self.conversations[session_id].append(
                    {"role": "assistant", "content": response}
                )

                return {
                    "response": response,
                    "function_call": None,
                    "session_id": session_id,
                }
            else:
                default_response = "I'm here to help you with trading on Injective Chain. You can ask me about trading, checking balances, making transfers, or staking. How can I assist you today?"
                self.conversations[session_id].append(
                    {"role": "assistant", "content": response}
                )

                return {
                    "response": response,
                    "function_call": None,
                    "session_id": session_id,
                }

        except Exception as e:
            error_response = f"I apologize, but I encountered an error: {str(e)}. How else can I help you?"
            return {
                "response": error_response,
                "function_call": None,
                "session_id": session_id,
            }

    def clear_history(self, session_id="default"):
        """Clear conversation history for a specific session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id="default"):
        """Get conversation history for a specific session."""
        return self.conversations.get(session_id, [])


# Initialize chat agent
agent = InjectiveChatAgent()

@app.before_request
@app.before_request
async def check_authorization_header():
    """Middleware to validate the authorization header."""
    authorization_header = request.headers.get("Authorization")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized: Missing or invalid Authorization header"}), 401

    token = authorization_header.split("Bearer ")[1]  # Extract token after "Bearer "
    if token != SECRET_KEY:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401


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
        
        print(f"Response content: {response}")
        print(f"Type of Response: {type(response)}")

        # Assuming response might be a dictionary or object, handle accordingly
        if isinstance(response, dict):
            # If response contains a key "response", extract it
            message = response.get("response", "No response message found")
        elif isinstance(response, str):
            message = response
        else:
            message = "Unexpected response format"

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
    """Clear chat history endpoint"""
    session_id = request.args.get("session_id", "default")
    agent.clear_history(session_id)
    return jsonify({"status": "success"})


def main():
    parser = argparse.ArgumentParser(description="Run the chatbot API server")
    parser.add_argument("--port", type=int, default=5000, help="Port for API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for API server")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()

    config = Config()
    config.bind = [f"{args.host}:{args.port}"]
    config.debug = args.debug

    print(f"Starting API server on {args.host}:{args.port}")
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    main()