from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool

from models.employee_payload import EmployeePayload
from services.biometry_engine import BiometryEngine
import json
import base64
import numpy as np
import os
router = APIRouter()

# Inicializa o motor UMA VEZ na subida da API
# Isso evita carregar o modelo pesado a cada requisição
engine = BiometryEngine()

@router.post("/biometria/gerar-vetor")
async def gerar_vetor(file: UploadFile = File(...)):
    """
    Recebe uma imagem (JPG/PNG), processa com InsightFace
    e retorna o vetor biométrico em Base64.
    """

    # 1. Validação de tipo
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Apenas arquivos JPG ou PNG são permitidos.")

    # 2. Leitura dos bytes
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # 3. Processamento (Síncrono pois é CPU Bound)
    # Como o InsightFace bloqueia a CPU, o ideal em produção é rodar isso
    # em um ThreadPool.
    # Configurado para usar uma threadPool para operações bloqueantes e melhorar a concorrência

    try:
        success, result = await run_in_threadpool(engine.generate_embedding, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not success:
        # Retorna 422 (Unprocessable Entity) ou 400 se a foto for ruim
        raise HTTPException(status_code=422, detail=result)

    return {
        "status": "success",
        "data": result
    }

@router.post("/biometria/comparar-vetor")
async def comparar_vetor(file: UploadFile = File(...)):
    """
    Recebe uma imagem, gera o embedding e compara com os templates em `templates.json`.
    A comparação é feita exclusivamente contra os templates persistidos em `templates.json`.
    Esse metodo é apenas para demonstração / testes para calculos de similaridade e será
    bloqueado para requisiçoes em produção.
    """
    # Validação simples de tipo
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Apenas arquivos JPG ou PNG são permitidos.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # Gera embedding da imagem recebida
    success, gen_result = engine.generate_embedding(file_bytes)
    if not success:
        raise HTTPException(status_code=422, detail=gen_result)

    probe_emb_b64 = gen_result.get("embedding_base64")

    # Carrega templates.json (espera-se que esteja no mesmo diretório deste módulo)
    current_dir = os.path.dirname(__file__)
    templates_path = os.path.join(current_dir, "templates.json")

    if not os.path.exists(templates_path):
        raise HTTPException(status_code=500, detail=f"Arquivo de templates não encontrado: {templates_path}")

    try:
        with open(templates_path, "r", encoding="utf-8") as f:
            templates_json = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao ler templates.json: {e}")

    # Normaliza diferentes formatos possíveis de templates.json para uma lista de templates
    def normalize_templates(obj):
        """Retorna uma lista de objetos que contêm 'embedding_base64'.
        Aceita como entrada: lista, dict (wrapper), dict com chaves comuns (templates/items/results),
        dict onde values podem ser templates ou listas de templates.
        """
        templates = []

        # Lista: processa cada item
        if isinstance(obj, list):
            for item in obj:
                templates.extend(normalize_templates(item))
            return templates

        # Dicionário: possíveis formatos
        if isinstance(obj, dict):
            # Caso simples: o próprio dict é um template
            if 'embedding_base64' in obj:
                return [obj]

            # Se houver 'data', processa seu conteúdo recursivamente
            if 'data' in obj:
                return normalize_templates(obj['data'])

            # Procura chaves usuais que contenham listas de templates
            for key in ('templates', 'items', 'results'):
                if key in obj:
                    return normalize_templates(obj[key])

            # Por fim, percorre os valores do dict procurando templates
            for v in obj.values():
                templates.extend(normalize_templates(v))
            return templates

        # Outros tipos: ignorar
        return []

    templates_list = normalize_templates(templates_json)

    if not templates_list:
        raise HTTPException(status_code=500, detail="Nenhum template encontrado em templates.json (formato inesperado)")

    # Pega o primeiro template salvo como base para gerar falsos
    base_template = templates_list[0]
    base_emb_b64 = base_template.get("embedding_base64")

    if base_emb_b64 is None:
        raise HTTPException(status_code=500, detail="Template salvo não contém 'embedding_base64'.")

    # Decodifica para numpy para gerar fakes
    try:
        base_bytes = base64.b64decode(base_emb_b64)
        base_emb = np.frombuffer(base_bytes, dtype=np.float32)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao decodificar embedding salvo: {e}")

    # NOTE: não geramos mais templates falsos aqui. A comparação será feita
    # exclusivamente contra os templates persistidos em `templates.json`.

    # Monta lista de templates a comparar: templates do arquivo
    compare_candidates = []

    # Aplica rótulos aos templates originais (mantemos qualquer metadado disponível)
    for idx, t in enumerate(templates_list):
        # Tenta achar um id útil
        tid = t.get('id') or t.get('name') or t.get('subject') or t.get('user_id') or f"template_file_{idx}"
        compare_candidates.append({
            "id": tid,
            "embedding_base64": t.get("embedding_base64"),
            "det_score": t.get("det_score"),
            "bbox": t.get("bbox")
        })

    # Compara todos com o embedding gerado
    comparisons = []
    for cand in compare_candidates:
        emb_b64 = cand.get("embedding_base64")
        if emb_b64 is None:
            continue
        ok, sim = engine.compare_embeddings(probe_emb_b64, emb_b64)
        if not ok:
            # Registramos o erro mas seguimos
            comparisons.append({
                "id": cand.get("id"),
                "error": sim
            })
        else:
            comparisons.append({
                "id": cand.get("id"),
                "similarity": sim,
                "det_score": cand.get("det_score"),
                "bbox": cand.get("bbox")
            })

    # Ordena por similaridade decrescente quando possível
    comparisons_sorted = sorted(comparisons, key=lambda x: x.get("similarity", -1), reverse=True)

    return {
        "status": "success",
        "data": {
            "probe": gen_result,
            "comparisons": comparisons_sorted
        }
    }

@router.post("/employee/payload")
async def employee_payload(data: EmployeePayload):
    if not data:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Enfileira o payload para processamento assíncrono (download S3 -> gerar embedding -> persistir)
    try:
        job_id = engine.enqueue_payload(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "accepted", "job_id": job_id}


@router.get("/employee/payload/{job_id}")
async def get_employee_job_status(job_id: str):
    try:
        job = engine.get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return {"status": "success", "job": job}


@router.get("/")
async def root():
    return {"message": "API de Geração Biométrica está rodando."}

# Observação: este módulo agora exporta `router`; monte a aplicação principal em `main.py` e inclua este router.
# Para desenvolvimento execute: uvicorn main:app --reload
