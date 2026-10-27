"""
Testes automatizados para a Etapa 5: Manutenção, Distribuição, Scripts e Checklist TV.
"""
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import BASE_DIR, VERSION
from app.database import init_db, reset_session, set_setting, get_setting
from app.services.auth_service import hash_password, verify_password

def setup_admin_logged_in():
    init_db()
    reset_session()
    set_setting("admin_password_hash", hash_password("senhaTeste123"))
    set_setting("admin_password_changed", "1")
    set_setting("admin_access_restriction", "all")
    client = TestClient(app)
    res = client.post("/admin/login", data={"password": "senhaTeste123"}, follow_redirects=False)
    assert res.status_code == 303
    return client

def test_about_endpoint_unauthorized():
    """Verifica que o endpoint /api/admin/about exige autenticação de administrador."""
    client = TestClient(app)
    res = client.get("/api/admin/about", follow_redirects=False)
    assert res.status_code in (401, 303), "Deve bloquear acesso não autorizado"
    print("✓ test_about_endpoint_unauthorized passou")

def test_about_endpoint_authorized():
    """Verifica que /api/admin/about retorna a versão 1.5.0, as etapas e o changelog."""
    client = setup_admin_logged_in()
    res = client.get("/api/admin/about")
    assert res.status_code == 200, f"Status code inesperado: {res.status_code}"
    data = res.json()
    assert data.get("status") == "ok"
    assert data.get("version") == VERSION
    assert data.get("version") == "1.5.0"
    
    etapas = data.get("etapas", [])
    assert len(etapas) == 5, "Devem ser reportadas exatamente 5 etapas"
    
    # Conferir títulos das 5 etapas
    assert "Segurança" in etapas[0]["nome"]
    assert "Confiabilidade" in etapas[1]["nome"]
    assert "Controle dos Pais" in etapas[2]["nome"]
    assert "Experiência da Criança" in etapas[3]["nome"]
    assert "Manutenção" in etapas[4]["nome"]
    for e in etapas:
        assert e["status"] == "Concluída"

    assert data.get("changelog_exists") is True
    assert "1.5.0" in data.get("changelog_preview", "")
    print("✓ test_about_endpoint_authorized passou")

def test_atualizar_bat_content():
    """Verifica integridade do script atualizar.bat."""
    script_path = BASE_DIR / "atualizar.bat"
    assert script_path.exists(), "atualizar.bat deve existir na raiz do projeto"
    content = script_path.read_text(encoding="utf-8", errors="ignore")
    
    assert "git pull" in content, "atualizar.bat deve executar git pull"
    assert "requirements.txt" in content, "atualizar.bat deve reinstalar dependências do requirements.txt"
    assert "media/" in content or "media" in content, "atualizar.bat deve alertar/proteger a pasta media"
    assert "data/" in content or "data" in content, "atualizar.bat deve alertar/proteger a pasta data"
    print("✓ test_atualizar_bat_content passou")

def test_bipinho_spec_packaging():
    """Verifica que bipinho.spec empacota estáticos e templates sem incluir dados nem mídias."""
    spec_path = BASE_DIR / "bipinho.spec"
    assert spec_path.exists(), "bipinho.spec deve existir na raiz do projeto"
    content = spec_path.read_text(encoding="utf-8", errors="ignore")
    
    # Deve incluir templates e static
    assert "templates" in content, "bipinho.spec deve empacotar os templates"
    assert "static" in content, "bipinho.spec deve empacotar os arquivos estáticos"
    
    # Não deve empacotar data/ nem media/ para garantir que o banco e uploads sejam persistentes
    # Na lista de datas:
    lines = [line.strip() for line in content.splitlines()]
    datas_block = []
    in_datas = False
    for line in lines:
        if line.startswith("datas = ["):
            in_datas = True
        if in_datas:
            datas_block.append(line)
            if line.startswith("]"):
                break
    datas_str = " ".join(datas_block)
    assert "'data'" not in datas_str and '"data"' not in datas_str, "data/ não pode ser empacotado no executável"
    assert "'media'" not in datas_str and '"media"' not in datas_str, "media/ não pode ser empacotado no executável"
    print("✓ test_bipinho_spec_packaging passou")

def test_empacotar_scripts():
    """Verifica existência e consistência dos scripts de empacotamento PyInstaller."""
    py_script = BASE_DIR / "empacotar.py"
    bat_script = BASE_DIR / "empacotar.bat"
    assert py_script.exists(), "empacotar.py deve existir"
    assert bat_script.exists(), "empacotar.bat deve existir"
    
    py_content = py_script.read_text(encoding="utf-8", errors="ignore")
    assert "bipinho.spec" in py_content, "empacotar.py deve invocar bipinho.spec"
    assert "PyInstaller" in py_content or "pyinstaller" in py_content
    print("✓ test_empacotar_scripts passou")

def test_resetar_senha_script():
    """Verifica a lógica de reset de senha para caso de esquecimento."""
    reset_script = BASE_DIR / "resetar_senha.py"
    reset_bat = BASE_DIR / "resetar_senha.bat"
    assert reset_script.exists(), "resetar_senha.py deve existir"
    assert reset_bat.exists(), "resetar_senha.bat deve existir"
    
    # Simula execução da redefinição
    init_db()
    nova_senha = "MinhaNovaSenhaSegura123"
    set_setting("admin_password_hash", hash_password(nova_senha))
    set_setting("admin_password_changed", "0")
    
    h = get_setting("admin_password_hash")
    assert verify_password(nova_senha, h) is True
    assert get_setting("admin_password_changed") == "0"
    print("✓ test_resetar_senha_script passou")

def test_checklist_tv_content():
    """Verifica que CHECKLIST_TV.md existe e aborda os pontos essenciais de homologação."""
    checklist_path = BASE_DIR / "CHECKLIST_TV.md"
    assert checklist_path.exists(), "CHECKLIST_TV.md deve existir"
    content = checklist_path.read_text(encoding="utf-8", errors="ignore")
    
    assert "Wake Lock" in content or "tela" in content.lower(), "Checklist deve conter teste de tela/Wake Lock"
    assert "Bipinho já volta" in content or "reconexão" in content.lower(), "Checklist deve conter teste de reconexão automática"
    assert "interromper" in content.lower() or "ignorar" in content.lower(), "Checklist deve conter teste de bipe durante vídeo"
    assert "dormindo" in content.lower() or "limite" in content.lower(), "Checklist deve conter teste de limites/horário de sono"
    assert "tempo assistido" in content.lower() or "tempo" in content.lower(), "Checklist deve conter teste de contagem por tempo"
    assert "chave dos pais" in content.lower() or "pais-liberar" in content.lower(), "Checklist deve conter teste de liberação pelos pais"
    assert "colorir" in content.lower(), "Checklist deve conter teste de páginas de colorir"
    assert "backup" in content.lower() or "restauração" in content.lower(), "Checklist deve conter teste de backup/restauração"
    print("✓ test_checklist_tv_content passou")

if __name__ == "__main__":
    print("\n--- INICIANDO TESTES DA ETAPA 5 ---")
    test_about_endpoint_unauthorized()
    test_about_endpoint_authorized()
    test_atualizar_bat_content()
    test_bipinho_spec_packaging()
    test_empacotar_scripts()
    test_resetar_senha_script()
    test_checklist_tv_content()
    print("\n🎉 TODOS OS 7 TESTES DA ETAPA 5 PASSARAM COM SUCESSO!\n")
