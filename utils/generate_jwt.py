import jwt
import datetime
import uuid

from models.employee_payload import ApiPayload


def api_cadastro_guilherme(data: ApiPayload):
    """
    Gera um token JWT baseado no contrato C# fornecido.
    """
    secret_key = "YAcq5t8e5yJ9bp/nilH98OgVExFd2poKw0wpmKy2eC0="
    issuer = "BiometriaApp"
    audience = "BiometriaApp"

    # Claims
    payload = {
        "username": "i9brgroup@crud",
        "EmployeeSiteID": data.siteId,
        "EmployeeLocalID": data.localId,
        "FingerID": None,
        "jti": str(uuid.uuid4()),
        "iss": issuer,
        "aud": audience,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
    }

    # Gerar Token usando HS256 (correspondente ao HmacSha256 do C#)
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    return token

def api_recuperar_templates(siteId: str):
    secret_key = "Sk9TRUxJVE8xNTc="
    issuer = "Authentication API - i9brgroup"
    subject = "junior_apipython@i9brgroup.com"

    payload = {
        "Username": "i9brgroup@python",
        "iss": issuer,
        "sub": subject,
        "siteId": siteId,
        "role": "SUPER_ADMIN",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")



