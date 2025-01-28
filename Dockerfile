FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    x11vnc \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libxkbcommon-x11-0 \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório para o app
WORKDIR /app

# Copiar dependências do projeto
COPY requirements.txt .

# Instalar dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o projeto para o contêiner
COPY . .

# Configuração da entrada do contêiner
CMD ["python", "main.py"]
