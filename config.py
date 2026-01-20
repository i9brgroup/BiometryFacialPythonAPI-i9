import configparser
import os
from pathlib import Path

# Carrega .env (formato INI) - usa caminho absoluto baseado na localização deste arquivo
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / '.env'

config = configparser.ConfigParser()
if ENV_FILE.exists():
    config.read(ENV_FILE, encoding='utf-8-sig')
    print(f"[CONFIG] Arquivo .env carregado de: {ENV_FILE}")
else:
    print(f"[CONFIG] AVISO: Arquivo .env não encontrado em: {ENV_FILE}")


def get_value(section: str, key: str, env_var: str = None, default: str = None):
    """Obtém valor: prioridade env var > .env > default"""
    if env_var and os.environ.get(env_var):
        return os.environ.get(env_var)
    try:
        return config.get(section, key)
    except Exception:
        return default


def get_db_config():
    """Retorna configurações do banco de dados SQL Server"""
    return {
        'DRIVER': get_value('mysql', 'DRIVER', 'DB_DRIVER'),
        'SERVER': get_value('mysql', 'SERVER', 'DB_SERVER'),
        'PORT': get_value('mysql', 'PORT', 'DB_PORT'),
        'DATABASE': get_value('mysql', 'DATABASE', 'DB_DATABASE'),
        'UID': get_value('mysql', 'UID', 'DB_UID'),
        'PWD': get_value('mysql', 'PWD', 'DB_PWD')
    }


def get_aws_config():
    """Retorna configurações AWS/S3"""
    # Tenta bucket em múltiplas seções
    bucket = (get_value('s3', 'BUCKET', 'BUCKET') or
              get_value('aws', 'BUCKET') or
              get_value('default', 'BUCKET'))

    aws_config = {
        'BUCKET': bucket,
        'AWS_ACCESS_KEY_ID': get_value('s3', 'AWS_ACCESS_KEY_ID', 'AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': get_value('s3', 'AWS_SECRET_ACCESS_KEY', 'AWS_SECRET_ACCESS_KEY'),
        'REGION': get_value('s3', 'REGION', 'AWS_REGION') or get_value('aws', 'REGION')
    }

    print(f"[CONFIG] AWS Config: BUCKET={bucket}, REGION={aws_config['REGION']}")
    return aws_config
