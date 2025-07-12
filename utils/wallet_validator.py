from solders.pubkey import Pubkey
from tonsdk.utils import Address

def is_valid_solana_address(address: str) -> bool:
    """
    Validate Solana wallet address.
    
    Args:
        address: Solana wallet address
    
    Returns:
        True if valid, False otherwise
    """
    try:
        Pubkey.from_string(address)
        return True
    except ValueError:
        return False

def is_valid_ton_address(address: str) -> bool:
    """
    Validate TON wallet address.
    
    Args:
        address: TON wallet address
    
    Returns:
        True if valid, False otherwise
    """
    try:
        Address(address)  # Проверяет формат и контрольную сумму TON-адреса
        return True
    except ValueError:
        return False
