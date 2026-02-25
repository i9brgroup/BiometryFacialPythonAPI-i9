from pathlib import Path
import pandas as pd
from models.employee_payload import EmployeePayload

def generate_files_csv(emp: EmployeePayload, face_template: str):
    diretorio = Path("data/employees")

    # 2. Cria a pasta caso ela não exista (parents=True cria pastas pai se necessário)
    diretorio.mkdir(parents=True, exist_ok=True)

    # 3. Define o caminho completo do arquivo
    caminho_arquivo = diretorio / f"employee_{emp.id}_{emp.name}.csv"

    colunas_csv = ['ID', 'firstname', 'lastname', 'badgenumber', 'employeelocalid', 'USER1', 'EMPLOYEESITEID',
                   'EMPLOYEEINACTIVE', 'FingerPrintTemplate', 'FacePrintTemplate', 'SUPERVISOR']

    dados = {
        'ID': emp.id,
        'firstname': emp.name,
        'lastname': '',
        'badgenumber': '',
        'employeelocalid': emp.localId,
        'USER1': '',
        'EMPLOYEESITEID': emp.siteId,
        'EMPLOYEEINACTIVE': '',
        'FingerPrintTemplate': '',
        'FacePrintTemplate': face_template,
        'SUPERVISOR': ''
    }

    df = pd.DataFrame([dados], columns=colunas_csv)

    # 3. Salve o CSV
    df.to_csv(caminho_arquivo, index=False, sep=',', encoding='utf-8')

    return df
