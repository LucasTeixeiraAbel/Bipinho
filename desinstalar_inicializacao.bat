@echo off
chcp 65001 >nul
title Bipinho - Remover Inicializacao com o Windows
cls

echo ========================================================
echo       REMOVER INICIALIZACAO AUTOMATICA DO BIPINHO
echo ========================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Bipinho.lnk"

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [SUCESSO] O atalho do Bipinho foi removido da inicializacao do Windows.
) else (
    echo [INFO] O Bipinho nao estava configurado para iniciar automaticamente.
)

echo.
pause
