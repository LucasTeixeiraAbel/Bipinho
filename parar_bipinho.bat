@echo off
chcp 65001 >nul
title Bipinho - Parar Servidor
cls

echo ========================================================
echo                 PARANDO O BIPINHO
echo ========================================================
echo.

echo Procurando processos em execucao na porta 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Encerrando processo PID %%a...
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [CONCLUIDO] Servidor Bipinho finalizado.
echo.
ping 127.0.0.1 -n 2 >nul
