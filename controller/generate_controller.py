import logging

from fastapi import APIRouter, HTTPException, Depends

import logger
from models.employee_payload import EmployeePayload, ApiPayload
from services.biometry_engine import BiometryEngine
from utils import generate_jwt
from utils.security import generate_api_key, generate_secret_service, get_api_key

router = APIRouter()

# Inicializa o motor UMA VEZ na subida da API
# Isso evita carregar o modelo pesado a cada requisição
engine = BiometryEngine()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenerateController")


@router.post("/employee/payload")
async def employee_payload(data: EmployeePayload, api_key: str = Depends(get_api_key)):
    if not data:
        raise HTTPException(status_code=400, detail="Invalid payload")
    try:
        result = engine.process_payload(data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro inesperado no endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def root():
    return {"message": "API de Geração Biométrica está rodando."}


@router.post("/api-key/generate")
async def generate_api_key_controller():
    """
    Gera uma chave de API única.
    Deve ser usada apenas se precisar criar uma nova chave de API.
    """
    api_key = generate_api_key()
    return {"key": api_key}

@router.get("/api-key/guilherme")
async def get_api_key_guilherme(data: ApiPayload):
    return generate_jwt.api_cadastro_guilherme(data=data)


@router.post("/secret-key/generate")
async def generate_secret_key_controller():
    """
    Gera uma chave secreta única.
    Deve ser usada apenas se precisar criar uma nova chave secreta.
    """
    secret_key = generate_secret_service()
    return {"secret_key": secret_key}

# Para desenvolvimento: uvicorn main:app --reload
