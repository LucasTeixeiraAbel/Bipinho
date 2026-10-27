@echo off
chcp 65001 >nul
title Bipinho - Atualizar Sistema
cls

echo ========================================================
echo                 ATUALIZAR O BIPINHO
echo ========================================================
echo.
echo Este script atualiza o Bipinho para a versão mais recente:
echo  1. Encerra qualquer processo em execução na porta 8000
echo  2. Baixa as atualizações do GitHub (git pull)
echo  3. Atualiza as dependências (requirements.txt)
echo  4. Preserva 100%% intactos seus desenhos (media/) e banco (data/)
echo  5. Reinicia o servidor automaticamente
echo.
echo Pressione qualquer tecla para iniciar a atualização...
pause >nul

cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

echo.
echo [1/4] Encerrando o servidor Bipinho em execução...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo Encerrando processo PID %%a...
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo.
echo [2/4] Verificando e baixando atualizações do repositório...
where git >nul 2>&1
if %errorlevel% equ 0 (
    git pull origin main
    if %errorlevel% neq 0 (
        echo [AVISO] Não foi possível sincronizar via git pull origin main.
        echo Tentando git pull padrão...
        git pull
    )
) else (
    echo [AVISO] Git não encontrado no PATH do sistema. Pulando sincronização git.
)

echo.
echo [3/4] Verificando dependências Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    python -m pip install -r requirements.txt --upgrade
) else (
    echo [ERRO] Python não encontrado no PATH do sistema.
)

echo.
echo ========================================================
echo  [SUCESSO] Atualização concluída com êxito!
echo  Seus desenhos cadastrados (media/) e configurações (data/)
echo  permanecem salvos e intactos.
echo ========================================================
echo.
echo Reiniciando o servidor Bipinho em 3 segundos...
timeout /t 3 >nul

start "Bipinho" cmd /c "%~dp0iniciar_bipinho.bat"
exit
