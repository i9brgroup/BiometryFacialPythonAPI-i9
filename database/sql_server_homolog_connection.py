from factory.abstract_factory import Connection
from logger import logging
from config import get_db_config
import pyodbc
import time

class SqlServerHomolog(Connection):
    def __init__(self):
        logging.info('Database service started, trying to connect to database')
        db_conf = get_db_config()
        # Carrega valores com fallback
        self.driver = db_conf.get('DRIVER')
        self.server = db_conf.get('SERVER')
        self.port = db_conf.get('PORT')
        self.database = db_conf.get('DATABASE')
        self.uid = db_conf.get('UID')
        self.pwd = db_conf.get('PWD')
        self.connection = None

        logging.info(f"DB Config - Server: {self.server}, Database: {self.database}, UID: {self.uid}")

    def connect(self):
        conected = False
        while not conected:
            logging.info('Trying connect a sql server database')
            try:
                conn_str = (
                    f"DRIVER={{{self.driver}}};SERVER={self.server};PORT={self.port};DATABASE={self.database};UID={self.uid};PWD={self.pwd};"
                )
                self.connection = pyodbc.connect(conn_str)
                self.cursor = self.connection.cursor()
                conected = True
                logging.info('Database connection established')
            except pyodbc.Error as e:
                logging.error('Error connecting to database', exc_info=True)
                time.sleep(20)

    def execute_query(self, query, params=None):
        if self.connection is None:
            logging.error("Erro: Nenhuma conexão ativa.")
            return False

        cursor = self.connection.cursor()
        try:
            if params:
                logging.info(f"Executando query com params: {params}")
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rows_affected = cursor.rowcount
            logging.info(f"Query executada. Linhas afetadas: {rows_affected}")

            try:
                rows = cursor.fetchall()
            except pyodbc.Error:
                # Algumas queries (INSERT/UPDATE) não retornam rows
                rows = None

            self.connection.commit()
            logging.info(f"Commit realizado com sucesso")

            # Retorna True se alguma linha foi afetada
            return rows_affected > 0 if rows_affected is not None else True

        except pyodbc.Error as ex:
            try:
                self.connection.rollback()
                logging.info("Rollback realizado")
            except Exception:
                pass
            logging.error(f"Erro na execução da query: {ex}")
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def close(self):
        """Fecha a conexão com o banco de dados"""
        if self.connection:
            try:
                self.connection.close()
                logging.info("Conexão com banco fechada")
            except Exception as e:
                logging.error(f"Erro ao fechar conexão: {e}")
