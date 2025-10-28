@echo off
title Servidor Flask - Estoque

ECHO ==========================================================
ECHO Iniciando a aplicacao de estoque (Backend)
ECHO ==========================================================

REM Caminho raiz do projeto
set "PROJECT_ROOT=C:\xampp\htdocs\estoque"

REM Caminho para o backend
set "BACKEND_PATH=%PROJECT_ROOT%\backend"

REM Caminho do ambiente virtual
set "VENV_PATH=%PROJECT_ROOT%\.venv"

ECHO Ativando o ambiente virtual...
call "%VENV_PATH%\Scripts\activate.bat"

IF ERRORLEVEL 1 (
    ECHO ERRO: Falha ao ativar o ambiente virtual!
    PAUSE
    EXIT /B 1
)

ECHO Navegando para o backend...
cd /d "%BACKEND_PATH%"

ECHO Iniciando o servidor Flask...
py run.py

ECHO.
ECHO Servidor Flask encerrado.