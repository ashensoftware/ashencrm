@echo off
title Ashen CRM - Dashboard
echo ==============================================
echo        Iniciando Ashen CRM Dashboard
echo ==============================================
echo.

cd /d "%~dp0"

echo [1/2] Iniciando Backend (FastAPI)...
start "Backend - Ashen CRM" cmd /c "call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --reload --port 8000"

echo [2/2] Iniciando Frontend (React/Vite)...
start "Frontend - Ashen CRM" cmd /c "cd frontend && npm run dev"

echo.
echo Los servicios se estan ejecutando en ventanas separadas.
echo El panel estara disponible en: http://localhost:5173
echo.
pause
