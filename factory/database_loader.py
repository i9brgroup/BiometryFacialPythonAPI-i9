from config import get_value
from factory.sql_server_homolog_factory import SqlServerHomologFactory
from logger import logging

def get_db_factory():
    db_type = get_value('type', 'DB_TYPE', 'DB_TYPE', 'HOMOLOG')
    logging.info(f"Tentando pegar a conexão do DB_TYPE: {db_type}")

    if db_type == "HOMOLOG":
        logging.info("Criando factory de banco HOMOLOG")
        factory = SqlServerHomologFactory()
        return factory
    elif db_type == "PROD":
        raise NotImplementedError("Production database not implemented yet")
    else:
        raise ValueError(f"Unknown database type: {db_type}")