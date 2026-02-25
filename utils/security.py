from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from keycove import hash, generate_secret_key, encrypt, generate_token

from config import get_api_key, get_secret_key, get_hashed_key
from logger import logging
from utils.key import Key

API_KEY = get_api_key()
ALGORITHEM = 'HS256'
HASHED_KEY = get_hashed_key()
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # 30 minutos
SECRET_KEY = get_secret_key()
"""
   Essa função gera uma chave de API única.
   Deve ser usada apenas se precisar criar uma nova chave de API.
"""
def generate_api_key():
    api_key_new = generate_token()
    hashed_key = hash(api_key_new)
    encrypted_key = encrypt(API_KEY, SECRET_KEY)
    new_key = Key(hashed_key=hashed_key, encrypted_key=encrypted_key)
    logging.info("CHAVE DE API GERADA COM SUCESSO")
    return {
        "api_key": api_key_new,
        "hashed_key": new_key.hashed_key,
        "encrypted_key": new_key.encrypted_key,
    }

def verify_api_key(provided_key: str) -> bool:
    hashed_provided_key = hash(provided_key)
    stored_hashed_key = hash_api_key()
    return hashed_provided_key == stored_hashed_key

def hash_api_key():
    return HASHED_KEY

def generate_secret():
    secret_key = generate_secret_key()
    encrypt(value_to_encrypt=API_KEY, secret_key=secret_key)
    return secret_key

def generate_secret_service():
    secret_key = generate_secret()
    return secret_key

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header and verify_api_key(api_key_header):
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
