from pydantic import BaseModel, SecretStr, HttpUrl
from functools import lru_cache
from yaml import load, SafeLoader
from typing import TypeVar, Type, Optional

ConfigType = TypeVar("ConfigType", bound=BaseModel)

class BotConfig(BaseModel):
    token: SecretStr

class DbConfig(BaseModel):
    host: str
    port: int
    user: str
    password: SecretStr
    database: str

class RhinoConfig(BaseModel):
    api_key: SecretStr

class MemeCoinConfig(BaseModel):
    contract_address: str
    fee_wallet: str
    min_swap_amount: float

class TonConnect(BaseModel):
    manifest: HttpUrl

@lru_cache(maxsize=1)
def parse_config_file() -> dict:
    try:
        with open("config.yaml", "rb") as file:
            config_data = load(file, Loader=SafeLoader)
        return config_data
    except FileNotFoundError:
        raise FileNotFoundError("config.yaml not found. Please ensure the config file is present.")
    except Exception as e:
        raise ValueError(f"Error loading config file: {e}")

def validate_config_data(config_dict: dict, root_key: str, model: Type[ConfigType]):
    if root_key not in config_dict:
        raise ValueError(f"Key {root_key} not found in configuration.")
    
    expected_keys = [key for key in model.__annotations__]
    for key in expected_keys:
        if key not in config_dict[root_key]:
            raise ValueError(f"Missing key '{key}' in '{root_key}' configuration.")

@lru_cache
def get_config(model: Optional[Type[ConfigType]], root_key: str) -> ConfigType:
    config_dict = parse_config_file()
    if model is None:
        if root_key not in config_dict:
            raise ValueError(f"Key {root_key} not found in configuration.")
        return config_dict[root_key]
    validate_config_data(config_dict, root_key, model)
    return model.model_validate(config_dict[root_key])
