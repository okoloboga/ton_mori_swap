from tonsdk.contract.token.ft import JettonWallet
from tonsdk.utils import Address, to_nano
from pytoniq_core import begin_cell
from base64 import urlsafe_b64encode

def encode_jetton_transfer(
        destination_address: str, 
        jetton_amount: int, 
        response_address: str = None, 
        forward_ton_amount: int = 0, 
        comment: str = None
) -> str:
    body = JettonWallet().create_transfer_body(
        destination=Address(destination_address),
        jetton_amount=to_nano(jetton_amount, "ton"),
        response_destination=Address(response_address) if response_address else None,
        forward_ton_amount=to_nano(forward_ton_amount, "ton") if forward_ton_amount else 0,
        forward_payload=begin_cell().store_uint(0, 32).store_string(comment).end_cell() if comment else None
    )
    return body.to_boc().hex()

def encode_comment_message(
        destination_address: str, 
        amount: int, 
        comment: str
) -> dict:
    return {
        'address': destination_address,
        'amount': str(amount),
        'payload': urlsafe_b64encode(
            begin_cell()
            .store_uint(0, 32)
            .store_string(comment)
            .end_cell()
            .to_boc()
        ).decode()
    }
