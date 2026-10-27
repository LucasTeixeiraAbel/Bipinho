"""
Script utilitário para redefinir a senha de administrador do Bipinho.
Uso no terminal:
    python resetar_senha.py
ou passando a senha direto:
    python resetar_senha.py MinhaNovaSenha123
"""
import sys
from app.database import init_db, set_setting
from app.services.auth_service import hash_password

def reset_admin_password():
    init_db()
    
    if len(sys.argv) > 1:
        new_password = sys.argv[1].strip()
    else:
        try:
            print("=" * 45)
            print("🔑 Bipinho — Redefinição de Senha do Admin")
            print("=" * 45)
            new_password = input("Digite a nova senha desejada: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperação cancelada.")
            return

    if not new_password or len(new_password) < 4:
        print("\n❌ Erro: A senha deve ter no mínimo 4 caracteres.")
        return

    # Salva hash seguro e marca como alterada
    hashed = hash_password(new_password)
    set_setting("admin_password_hash", hashed)
    set_setting("admin_password_changed", "1")
    
    print("\n✅ Senha de administrador redefinida com sucesso!")
    print(f"👉 Nova senha definida: {new_password}")
    print("Você já pode fazer login em: http://localhost:8000/admin")

if __name__ == "__main__":
    reset_admin_password()
