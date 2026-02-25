# Use uma imagem base oficial do Python
FROM python:3.11-slim

# Evita que o Python gere arquivos .pyc e que o output do log seja bufferizado
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema necessárias para:
# 1. ODBC Driver do SQL Server (pyodbc)
# 2. Bibliotecas auxiliares da OpenCV (libGL, libglib)
# 3. Ferramentas de compilação para pacotes Python (Cython, etc.)
# Instalar dependências do sistema e drivers Microsoft
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    g++ \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho no container
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que o FastAPI usará
EXPOSE 8000

# Comando para rodar a aplicação usando uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
