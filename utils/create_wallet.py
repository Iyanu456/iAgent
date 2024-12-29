from eth_account import Account
import secrets
import bech32


def get_injective_address(evm_address: str) -> str:
    """
    Converts an Ethereum address to an Injective address using bech32 encoding.
    """
    # Strip the '0x' prefix and convert hex address to bytes
    evm_bytes = bytes.fromhex(evm_address[2:])
    # Convert to bech32 (Injective address prefix: 'inj')
    injective_address = bech32.bech32_encode("inj", bech32.convertbits(evm_bytes, 8, 5))
    return injective_address


def create_injective_wallet():
    """
    Creates a new Injective wallet.
    Returns:
        dict: A dictionary containing the EVM address, Injective address, and private key.
    """
    # Generate a new Ethereum wallet
    private_key = "0x" + secrets.token_hex(32)  # Generate a random 32-byte hex key
    account = Account.from_key(private_key)

    # Get the EVM address
    evm_address = account.address

    # Convert the EVM address to an Injective address
    injective_address = get_injective_address(evm_address)

    return {
        "evmAddress": evm_address,
        "injectiveAddress": injective_address,
        "privateKey": private_key,
    }
