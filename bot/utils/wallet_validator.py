import base58

def is_valid_solana_address(address: str) -> bool:
    try:
        decoded = base58.b58decode(address)
        return len(decoded) == 32  # Solana-адреса — 32 байта
    except:
        return False

def is_valid_ton_address(address: str) -> bool:
    # Упрощенная проверка (заменить на реальную для TON)
    return len(address) > 0 and address.startswith("EQ") or address.startswith("UQ")
