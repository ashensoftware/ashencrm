@echo off
title Ashen CRM Dashboard
cd /d "%~dp0"
python data/scripts/run_crm.py %*
