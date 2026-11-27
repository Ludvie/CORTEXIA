@echo off
setlocal
cd /d "%~dp0..\backend"
rem Load configured values first, then supply defaults for local development.
.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017'); os.environ.setdefault('DB_NAME', 'cortexia'); os.environ.setdefault('CORS_ORIGINS', 'http://localhost:3000'); import uvicorn; uvicorn.run('server:app', host='127.0.0.1', port=8001)"
