import click
import replicate
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Configure Replicate client
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

@click.group()
def cli():
    """CLI for Injective iAgent"""
    pass

@cli.command()
@click.option('--prompt', required=True, help='Prompt for the AI model')
def generate_text(prompt):
    """Generate text using Meta AI"""
    try:
        # Replace with your specific Replicate model and input
        model = "meta/llama-2"  # Example: Meta AI model
        version = "latest"
        
        output = client.predict(
            model=model,
            version=version,
            inputs={"prompt": prompt}
        )
        
        click.echo("AI Response:")
        click.echo(output)

    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    cli()
