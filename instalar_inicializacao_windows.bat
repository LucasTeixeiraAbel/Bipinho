@echo off
chcp 65001 >nul
title Bipinho - Instalar Inicializacao com o Windows
cls

echo ========================================================
echo       CONFIGURAR INICIALIZACAO AUTOMATICA DO BIPINHO
echo ========================================================
echo.

cd /d "%~dp0"
set "TARGET_VBS=%~dp0iniciar_em_segundo_plano.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Bipinho.lnk"

echo Criando atalho na pasta Inicializar do Windows...
echo Pasta de destino: %STARTUP_FOLDER%
echo.

powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = '%TARGET_VBS%'; $sc.WorkingDirectory = '%~dp0'; $sc.Description = 'Servidor Bipinho'; $sc.Save()"

if %errorlevel% equ 0 (
    echo [SUCESSO] O Bipinho agora sera iniciado automaticamente sempre que o Windows ligar!
    echo.
    echo Local do atalho: "%SHORTCUT_PATH%"
    echo.
) else (
    echo [ERRO] Nao foi possivel criar o atalho.
    echo.
)

pause
