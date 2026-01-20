from factory.database_loader import get_db_factory
from logger import logging
from models.employee_payload import EmployeePayload


def insert_in_database(data: EmployeePayload, face_template: str):
    # Suporta várias variações de nomes que podem vir do payload Java
    key_photo = getattr(data, 'photoKey', None) or getattr(data, 'photo_key', None) or getattr(data, 'key_photo', None)
    target_id = getattr(data, 'id', None)
    target_site_id = getattr(data, 'siteId', None) or getattr(data, 'site_id', None) or getattr(data, 'siteID', None)
    target_loca_id = getattr(data, 'localId', None) or getattr(data, 'local_id', None) or getattr(data, 'locaID', None)

    logging.info(f"insert_in_database chamado - ID: {target_id}, Site: {target_site_id}, Loca: {target_loca_id}, Photo: {key_photo}")

    db_connection = None
    try:
        factory = get_db_factory()
        db_connection = factory.create_connection()
        db_connection.connect()
        logging.info("Conexão com banco estabelecida")

        query = """
                UPDATE EMPLOYEE
                SET faceTemplate = ?,
                    keyPhoto = ?
                WHERE ID = ?
                  AND EmployeeSiteID = ?
                  AND EmployeeLocalID = ?
                """

        # 4. A Tupla de Parâmetros (na ordem exata dos '?')
        params = (
            face_template,
            key_photo,
            target_id,
            target_site_id,
            target_loca_id
        )
        logging.info(f"Executando query de atualização de faceTemplate para ID {target_id} da empresa: {target_site_id}...")

        sucess = db_connection.execute_query(query, params)
        if sucess:
            logging.info("Dados inseridos com sucesso no banco")
            logging.info('ALL DONE - HAVE SUCCESSFULLY')
        else:
            logging.error("execute_query retornou False - nenhuma linha foi atualizada")
            raise Exception("Nenhuma linha foi atualizada no banco. Verifique se o registro existe.")

    except Exception as error:
        logging.error(f"Erro ao inserir no banco: {error}")
        raise  # Propaga a exceção para o caller
    finally:
        # Garante que a conexão seja fechada
        if db_connection:
            try:
                db_connection.close()
                logging.info("Conexão com banco fechada")
            except Exception as e:
                logging.error(f"Erro ao fechar conexão: {e}")