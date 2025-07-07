from aiogram.fsm.state import State, StatesGroup

class SwapForm(StatesGroup):
    solana_wallet = State()
    bridge_amount = State()
    bridge_confirm = State()
    bridge_tx_hash = State()
    usdt_amount = State()
    swap_amount = State()
    swap_confirm = State()
    coin_count = State()
