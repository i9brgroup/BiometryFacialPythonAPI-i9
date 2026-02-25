import base64
import io
import logging

import boto3
import cv2
import numpy as np
import requests
from botocore.exceptions import ClientError
from fastapi import HTTPException

from config import get_aws_config
from models.employee_payload import EmployeePayload
from services.database_service import insert_in_database
from services.generate_files_csv import generate_files_csv

# Tenta importar o InsightFace
try:
    from insightface.app import FaceAnalysis
except ImportError:
    raise ImportError("Instale a biblioteca: pip install insightface onnxruntime")

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BiometryEngine")

class BiometryEngine:
    def __init__(self):

        logger.info("Inicializando InsightFace (Modelo buffalo_s)...")
        try:
            # Carrega configurações AWS do .env
            aws_conf = get_aws_config()
            self.bucket = aws_conf.get('BUCKET')
            self.access_key = aws_conf.get('AWS_ACCESS_KEY_ID')
            self.secret_key = aws_conf.get('AWS_SECRET_ACCESS_KEY')
            self.region = aws_conf.get('REGION')

            logger.info(f"Configuração AWS carregada - Bucket: {self.bucket}, Region: {self.region}")

            # Cria cliente S3 com as credenciais do .env
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            logger.info("Cliente S3 configurado com credenciais do .env")

            # Mantemos CPUExecutionProvider para compatibilidade, mas no servidor
            # se tiver GPU, pode usar CUDAExecutionProvider
            self.app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])

            # Aumentei para 640x640 para o cadastro ter mais qualidade que a catraca
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("Motor Biométrico pronto.")
        except Exception as e:
            logger.critical(f"Erro fatal ao iniciar InsightFace: {e}")
            raise e

    def _bytes_to_image(self, image_bytes: bytes):
        """Converte bytes brutos (upload) para formato OpenCV (numpy array)"""
        try:
            # Converte bytes para array numpy uint8
            nparr = np.frombuffer(image_bytes, np.uint8)
            # Decodifica para imagem colorida
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Erro ao decodificar imagem: {e}")
            return None

    def generate_embedding(self, image_input):
        """
        Recebe a imagem em bytes ou em numpy.ndarray (OpenCV) e retorna o embedding.
        image_input: bytes | bytearray | numpy.ndarray
        Retorna: (sucesso: bool, dados: dict | str)
        """
        # Aceita bytes (upload/S3) ou np.ndarray (já decodificado pelo OpenCV)
        img = None
        if isinstance(image_input, (bytes, bytearray)):
            img = self._bytes_to_image(image_input)
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            return False, "Formato de imagem inválido. Forneça bytes ou numpy.ndarray."

        if img is None:
            return False, "Arquivo de imagem inválido ou corrompido."

        try:
            # O passo mágico: Detecção + Alinhamento + Embedding
            faces = self.app.get(img)
        except Exception as e:
            logger.error(f"Erro no app.get do InsightFace: {e}")
            return False, f"Erro interno de IA: {str(e)}"

        if not faces:
            return False, "Nenhum rosto detectado na imagem."

        # REGRA DE NEGÓCIO: Pegar o maior rosto (o mais próximo da câmera)
        # O cadastro não deve aceitar foto com 2 pessoas, mas se tiver alguém no fundo,
        # pegamos o rosto principal.
        faces.sort(key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
        target_face = faces[0]

        # Validação de Qualidade Mínima (Opcional, mas recomendado)
        if target_face.det_score < 0.60:
            return False, "Qualidade da detecção muito baixa. Tente outra foto."

        # Extração do vetor normalizado
        embedding = None
        if hasattr(target_face, 'normed_embedding') and target_face.normed_embedding is not None:
            embedding = target_face.normed_embedding
        elif hasattr(target_face, 'embedding') and target_face.embedding is not None:
            # Normalização manual se necessário
            emb = np.array(target_face.embedding, dtype=np.float32).flatten()
            norm = np.linalg.norm(emb)
            if norm > 1e-6:
                embedding = emb / norm

        if embedding is None:
            return False, "Falha ao gerar vetor biométrico."

        # Retorno pronto para salvar no Banco ou JSON
        # Convertemos para Base64 (string) pois é mais fácil de trafegar que lista de floats
        embedding_bytes = embedding.astype(np.float32).tobytes()
        embedding_base64 = base64.b64encode(embedding_bytes).decode('utf-8')

        return True, {
            "embedding_base64": embedding_base64,  # Para salvar no 'template'
            "det_score": float(target_face.det_score),
            "bbox": target_face.bbox.astype(int).tolist()  # Para desenhar o crop no front se quiser
        }

    def compare_embeddings(self, emb_base64_1: str, emb_base64_2: str):
        """
        Compara dois embeddings em Base64 e retorna a similaridade (cosine similarity).
        Retorna: (sucesso: bool, dados: float | str)
        """
        try:
            # Decodifica Base64 para bytes
            emb_bytes_1 = base64.b64decode(emb_base64_1)
            emb_bytes_2 = base64.b64decode(emb_base64_2)

            # Converte bytes para numpy arrays
            emb1 = np.frombuffer(emb_bytes_1, dtype=np.float32)
            emb2 = np.frombuffer(emb_bytes_2, dtype=np.float32)

            if emb1.shape != emb2.shape:
                return False, "Os vetores biométricos têm dimensões diferentes."

            # Calcula similaridade do cosseno
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)

            if norm1 < 1e-6 or norm2 < 1e-6:
                return False, "Um dos vetores biométricos é inválido."

            # Forçar float para evitar advertências de tipo e garantir compatibilidade
            similarity = float(dot_product) / (float(norm1) * float(norm2))

            return True, float(similarity)
        except Exception as e:
            logger.error(f"Erro ao comparar embeddings: {e}")
            return False, f"Erro ao comparar vetores biométricos: {str(e)}"


    def process_payload(self, data: EmployeePayload):
        """
        Processa o payload do funcionário, gera embedding e retorna resultado.
        Retorna: (sucesso: bool, dados: dict | str)
        """
        # Esperamos que o payload contenha a referência S3 em `photoKey`
        photo_key = getattr(data, 'photoKey', None) or getattr(data, 'photo_key', None) or getattr(data, 'key_photo', None)
        if not photo_key:
            return False, "Payload não contém 'photoKey' com a referência S3."

        # Obtém bucket S3 via config (usa self.bucket inicializado no __init__)
        bucket = self.bucket
        if not bucket:
            return False, f"Bucket S3 não configurado. Verifique o .env. Bucket atual: {bucket}"

        logger.info(f"Processando payload - Bucket: {bucket}, Key: {photo_key}")

        # Baixa imagem do S3 e gera embedding (download_img_from_s3 retorna dict ou levanta HTTPException)
        try:
            s3_response = self.download_img_from_s3(bucket, photo_key)
        except HTTPException as he:
            return False, f"Falha ao baixar/processar imagem do S3: {he.detail}"
        except Exception as e:
            return False, f"Erro inesperado ao baixar/processar S3: {e}"

        # Extrai embedding base64
        embedding_base64 = None
        if isinstance(s3_response, dict):
            embedding_base64 = s3_response.get('embedding')

        if not embedding_base64:
            logger.error(f"S3 response não contém embedding. Response: {s3_response}")
            return False, "Não foi possível obter embedding da imagem baixada do S3."

        logger.info(f"Embedding gerado com sucesso. Tamanho: {len(embedding_base64)} caracteres")

        try:
            logger.info(f"Iniciando persistência no banco para: {getattr(data, 'name', 'N/A')}")
            insert_in_database(data, embedding_base64)
            logger.info("Embedding persistido no banco com sucesso!")
        except Exception as e:
            # Logamos e retornamos erro — caller pode optar por retry
            logger.error(f"Falha ao inserir embedding no banco: {e}")
            return False, f"Falha ao inserir embedding no banco: {e}"

        # Sucesso: retorna o embedding para o caller
        logger.info("process_payload concluído com sucesso")
        return {"status" : "done", "embedding": embedding_base64}

    def download_img_from_s3(self, bucket: str, key_or_url: str):
        try:
            file_stream = io.BytesIO()
            resp = None

            # 1. Tenta identificar se key_or_url é uma URL ou apenas a chave do objeto
            is_url = key_or_url.startswith("http://") or key_or_url.startswith("https://")

            if is_url:
                # Se for URL, tenta baixar via requests
                try:
                    logger.info(f"Baixando imagem via URL: {key_or_url[:100]}...")
                    resp = requests.get(key_or_url, stream=True, timeout=15)
                    resp.raise_for_status()
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            file_stream.write(chunk)
                    file_stream.seek(0)
                except requests.RequestException as re:
                    logger.error(f"Falha ao baixar via URL: {re}")
                    raise HTTPException(status_code=400, detail=f"Erro ao baixar imagem da URL: {str(re)}")
            else:
                # Se não for URL, assume que é a Key e baixa via boto3
                try:
                    logger.info(f"Baixando imagem via Boto3 - Bucket: {bucket}, Key: {key_or_url}")
                    self.s3_client.download_fileobj(bucket, key_or_url, file_stream)
                    file_stream.seek(0)
                except ClientError as ce:
                    logger.error(f"Erro Boto3 ao baixar do S3: {ce}")
                    # Tenta fallback gerando URL se falhar o download_fileobj (opcional, mas aqui vamos subir o erro)
                    raise HTTPException(status_code=400, detail=f"Erro S3: {str(ce)}")

            # 2. Lê os bytes brutos do arquivo na memória
            raw_bytes = file_stream.read()
            file_stream.close()

            if not raw_bytes:
                raise HTTPException(status_code=400, detail="Objeto S3 vazio ou inválido")

            # 3. Validação rápida: tenta decodificar para garantir que é uma imagem
            img = self._bytes_to_image(raw_bytes)
            if img is None:
                raise HTTPException(status_code=400, detail="Arquivo S3 não é uma imagem válida")

            # 4. Gera embedding
            success, result = self.generate_embedding(img)
            if not success:
                raise HTTPException(status_code=400, detail=str(result))

            embedding_base64 = result.get("embedding_base64") if isinstance(result, dict) else None
            response = {"status": "sucesso"}
            if embedding_base64:
                response.update({
                    "embedding": embedding_base64,
                    "det_score": result.get("det_score"),
                    "bbox": result.get("bbox")
                })
            else:
                response["embedding"] = result

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Erro no download/processamento do S3: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if 'resp' in locals() and resp is not None:
                try:
                    resp.close()
                except:
                    pass
