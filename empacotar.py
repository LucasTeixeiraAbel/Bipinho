"""
empacotar.py — Script para empacotamento opcional do Bipinho com PyInstaller.
Gera um executável independente (bipinho.exe) que roda em qualquer PC Windows
sem precisar de Python previamente instalado.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_packaging():
    print("=" * 60)
    print("  📦 BIPINHO — EMPACOTAMENTO COM PYINSTALLER")
    print("=" * 60)
    print()

    # Check if pyinstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller encontrado (versão {PyInstaller.__version__})")
    except ImportError:
        print("PyInstaller não está instalado neste ambiente Python.")
        print("Instalando PyInstaller via pip...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=False)
        if res.returncode != 0:
            print("\n❌ Erro ao instalar o PyInstaller. Verifique sua conexão de rede ou pip.")
            return False

    spec_file = BASE_DIR / "bipinho.spec"
    if not spec_file.exists():
        print(f"❌ Arquivo de especificação '{spec_file.name}' não encontrado.")
        return False

    print("\nIniciando geração do executável com bipinho.spec...")
    print("Isso pode levar de 1 a 3 minutos dependendo do seu computador...\n")

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)]
    res = subprocess.run(cmd, cwd=str(BASE_DIR))

    if res.returncode == 0:
        dist_exe = BASE_DIR / "dist" / "bipinho.exe"
        print("\n" + "=" * 60)
        print("  🎉 EMPACOTAMENTO CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        if dist_exe.exists():
            size_mb = round(dist_exe.stat().st_size / (1024 * 1024), 2)
            print(f"Executável gerado: {dist_exe} ({size_mb} MB)")
            print("\nInstruções de uso:")
            print("1. Você pode mover o arquivo 'bipinho.exe' para qualquer pasta.")
            print("2. Ao executar, as pastas 'data/' e 'media/' serão criadas ao lado dele.")
            print("3. Nenhum vídeo nem banco foi embutido no .exe, garantindo portabilidade!")
        return True
    else:
        print("\n❌ Falha na geração do executável pelo PyInstaller.")
        return False

if __name__ == "__main__":
    success = run_packaging()
    if not success:
        sys.exit(1)
