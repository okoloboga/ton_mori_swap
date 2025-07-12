from aiogram.fsm.state import State, StatesGroup

class BridgeForm(StatesGroup):
    amount = State()
    solana_wallet = State()
    connect_wallet = State()
    wallet_connected = State()
    confirm_transaction = State()
    bridge_confirm = State()
