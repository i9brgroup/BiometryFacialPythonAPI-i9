BiometryEngine
===============

Descrição geral
---------------

O BiometryEngine é uma API em Python (FastAPI) responsável por processar imagens faciais, gerar embeddings (representações vetoriais da face) e persistir esses embeddings junto com o payload recebido no banco de dados. O fluxo principal é:

- Receber uma requisição POST (controller) com informações para gerar o processamento.
- Baixar a imagem do S3 para a memória.
- Gerar o embedding da imagem (no método principal `process_payload`).
- Inserir/consultar no banco de dados o payload recebido junto com o embedding em base64 (por meio do método `insert_in_database`).

Observação importante sobre comparações com templates
----------------------------------------------------

Importante: o fluxo de produção do sistema NÃO realiza comparações em memória contra os templates armazenados em `templates.json`.

O propósito primordial do sistema é:
- Receber o payload do frontend;
- Baixar a imagem do S3 via a key passada no payload;
- Gerar o embedding a partir da imagem;
- Persistir os dados do payload e o embedding gerado no banco de dados.

A comparação entre embeddings (por exemplo, contra templates salvos em `templates.json`) é apenas uma funcionalidade de testes e demonstração. Não será executada no `process_payload` nem em produção.

Funcionalidades
---------------

- Endpoint HTTP (FastAPI) que aciona o processamento de payloads faciais.
- Download de imagens a partir do S3 para memória (método `download_img_from_s3`).
- Geração de embeddings faciais a partir da imagem (método `process_payload`).
- Fila/Broker interno para enfileirar downloads do S3 e geração de embeddings de forma assíncrona e controlada.
- Persistência do payload e do embedding no banco de dados (via `insert_in_database`).
- Logging das etapas de execução e rastreamento de erros.

Por que não comparar com templates em memória no fluxo principal?
----------------------------------------------------------------

- Separação de responsabilidades: o trabalho de gerar um embedding e persistir dados deve ser distinto do serviço de busca/matching. Isso simplifica erros, retrys e auditoria.
- Escalabilidade: comparar em memória com um arquivo JSON não escala e é ineficiente para grandes volumes. Produção deve usar um serviço de busca vetorial (FAISS, Milvus, Pinecone, pgvector) ou delegar a busca ao banco.
- Consistência e segurança: templates em disco podem ficar desatualizados ou representar dados sensíveis. Persistir tudo no banco e fazer buscas controladas evita leaks.
- Latência e disponibilidade: persistir primeiro torna o caminho de escrita resiliente; o matching pode ser feito de forma assíncrona por outro serviço/worker.
- Precisão e métricas: a comparação para produção requer limiares, calibração e monitoramento — isso é diferente de testes ad-hoc contra `templates.json`.

Recomendação
------------

- Mantenha `process_payload` enxuto: gere o embedding, valide qualidade mínima e persista.
- Se precisar de matching em produção, use uma solução dedicada para busca vetorial ou uma tabela indexada no banco de dados, preferencialmente executada por um serviço separado.
- Para testes locais, mantenha endpoints ou utilitários que façam comparação contra `templates.json`, mas zelando para que esses endpoints não fiquem expostos em produção.

Fluxo principal (resumido)
--------------------------

1. O controlador (`controller/generate_controller.py`) expõe um endpoint POST que recebe o payload do sistema Java.
2. O controller envia a tarefa para a fila interna: enfileira o download do S3 e a geração do embedding.
3. Um worker (consumidor) retira a tarefa da fila, chama `download_img_from_s3` para obter a imagem em memória.
4. O worker chama `process_payload`, que gera o embedding (base64) e chama `insert_in_database` para persistir o payload + embedding no banco.
5. O worker registra o resultado e devolve resposta apropriada (ou o controller retorna um job id imediatamente e o resultado fica assíncrono, conforme implementação).

Arquitetura técnica
-------------------

Componentes principais:
- `main.py` — ponto de entrada da aplicação FastAPI. Inicia a aplicação (com `uvicorn main:app`) e registra os routers.
- `controller/generate_controller.py` — expõe os endpoints e coloca tarefas na fila de processamento.
- `services/biometry_engine.py` — contém a lógica de geração de embeddings e helpers de processamento (incluindo `process_payload`).
- `services/database_service.py` — abstração para operações de banco (inserções, queries).
- `database/sql_server_homolog_connection.py` — conexão com SQL Server para homologação (exemplo de fábrica/implementação).
- `factory/` — abstração de fábricas para escolher a implementação de banco e loaders de configuração.
- `utils/parse_templates.py` — utilitários para carregar e parsear `templates.json` (apenas para testes locais).
- `utils/test_compare.py` — utilitários de comparação entre embeddings (distância/cosseno, limiares) usados apenas para desenvolvimento/teste.

Fila de processamento:
- Implementação sugerida: uma fila interna simples baseada em asyncio.Queue ou queue.Thread/ThreadPool para processamento assíncrono e concorrente (workers consumidores). A fila enfileira tarefas que contêm: identificação do job, chave S3, payload Java.

Persistência de templates:
- `templates.json` permanece disponível para testes locais e deve ser carregado apenas por utilitários/handlers de teste. O fluxo de produção não o utiliza para matching.

Configuração (arquivo .ini)
---------------------------

Crie um arquivo `config.ini` na raiz do projeto com as seções mínimas para banco e AWS. Exemplo sugerido:

[aws]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
aws_region = us-east-1
s3_bucket = your-bucket-name
s3_endpoint =

[database]
db_driver = sqlserver
db_host = your-db-host
db_port = 1433
db_name = your_db
db_user = your_user
db_password = your_password

[app]
host = 0.0.0.0
port = 8000
workers = 4
queue_maxsize = 100

Observações de segurança:
- Nunca comite credenciais reais no repositório. Use variáveis de ambiente, secrets manager ou arquivos `.env` com gitignore.

Stack utilizada
----------------

- Linguagem: Python 3.11+
- Framework web: FastAPI
- Server ASGI: Uvicorn
- Biblioteca AWS S3: boto3 (ou alternativa compatível)
- Banco de dados: Microsoft SQL Server (driver: pyodbc ou sqlalchemy+pyodbc)
- Gerenciamento de dependências: pip / requirements.txt (sugestão)
- Logging: módulo `logging` do Python (arquivo `logger.py` no projeto)

Como rodar (desenvolvimento)
----------------------------

1. Crie um ambiente virtual e instale dependências mínimas (exemplo):

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt

2. Ajuste `config.ini` com as credenciais e endpoints corretos.
3. Inicie a aplicação:

   uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Notas e próximos passos sugeridos
--------------------------------

- Garantir que `process_payload` permaneça responsível apenas por geração e persistência de embeddings.
- Implementar um serviço separado, caso necessário, para "matching" (busca vetorial) e mantê-lo desacoplado do fluxo de escrita.
- Adicionar testes unitários para: parsing de templates, geração de embeddings (mock), e integração do worker.
- Documentar o contrato do endpoint POST (ex.: body esperado, exemplos) no próprio `controller/generate_controller.py` ou usando OpenAPI/Swagger (já fornecido por FastAPI).


Arquivo de referência
---------------------
- `main.py` — ponto de entrada da app
- `controller/generate_controller.py` — endpoints REST
- `services/biometry_engine.py` — lógica de processamento
- `utils/parse_templates.py` — carregamento e parsing de `templates.json` (apenas para testes)


Licença
-------

(Adicione aqui sua licença, se aplicável)
