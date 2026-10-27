@echo off
chcp 65001 >nul
title Bipinho - Empacotar com PyInstaller
cls

echo ========================================================
echo         EMPACOTAR BIPINHO COM PYINSTALLER
echo ========================================================
echo.
echo Este script cria um executavel Windows independente (bipinho.exe)
echo que funciona sem precisar ter o Python instalado.
echo.
pause

cd /d "%~dp0"
python empacotar.py

echo.
pause
