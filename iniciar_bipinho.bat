@echo off
chcp 65001 >nul
title Bipinho - Servidor de Desenhos
cls

echo ========================================================
echo                 INICIANDO O BIPINHO
echo ========================================================
echo.

cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no sistema!
    echo Por favor, instale o Python 3.10 ou superior e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Iniciando o servidor na porta 8000...
echo.
python run.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O servidor parou com codigo %errorlevel%.
    pause
)
