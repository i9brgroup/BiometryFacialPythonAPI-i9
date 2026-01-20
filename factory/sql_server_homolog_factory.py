from database.sql_server_homolog_connection import SqlServerHomolog
from factory.abstract_factory import ConnectionFactory, Connection


class SqlServerHomologFactory(ConnectionFactory):
    def create_connection(self) -> Connection:
        return SqlServerHomolog()
