from pydantic import BaseModel


class Key(BaseModel):
    hashed_key: str
    encrypted_key: str