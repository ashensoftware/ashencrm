@echo off
title Ashen CRM Dashboard
cd /d "%~dp0"
REM Recarga sola al editar codigo: API con uvicorn --reload (carpeta backend) + Vite en frontend.
REM Dashboard en desarrollo: http://localhost:5173  |  API: http://localhost:8000
REM Ver logs en consola: iniciar_crm.bat --logs
python data/scripts/run_crm.py %*
