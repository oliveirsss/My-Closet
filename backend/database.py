import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("❌ As chaves SUPABASE_URL e SUPABASE_KEY não foram encontradas no .env")

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
        user = supabase.auth.get_user(clean_token)
        return user
    except Exception as e:
        print(f"Auth Error: {e}")
        return None