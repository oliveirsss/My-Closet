import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Carregar variáveis de ambiente
load_dotenv()

url: Optional[str] = os.environ.get("SUPABASE_URL")
key: Optional[str] = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError(
        "❌ As chaves SUPABASE_URL e SUPABASE_KEY não foram encontradas no .env"
    )

# Inicializar Cliente Supabase
supabase: Client = create_client(url, key)


# --- Helper de Autenticação (Partilhado) ---
def get_user_from_token(token: str):
    """
    Verifica o token JWT e retorna o utilizador se for válido.
    """
    if not token:
        return None
    try:
        # Remove "Bearer " se existir
        clean_token = token.replace("Bearer ", "")
        user_response = supabase.auth.get_user(clean_token)

        # In newer supabase-py, it returns a UserResponse object.
        # We need to access .user property.
        if user_response and hasattr(user_response, "user"):
            return user_response

        return user_response
    except Exception as e:
        print(f"Auth Error: {e}")
        return None
