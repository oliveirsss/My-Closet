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
        user_response = supabase.auth.get_user(clean_token)
        
        # In newer supabase-py, it returns a UserResponse object.
        # We need to access .user property.
        if user_response and hasattr(user_response, 'user'):
             return user_response # returning the response object wrapper which has .user is fine if downstream uses .user
             # Wait, existing code uses user.user.id. 
             # If get_user returns UserResponse, then user.user.id is correct (UserResponse.user.id).
             # BUT if get_user fails, does it return None?
        
        return user_response 
    except Exception as e:
        print(f"Auth Error: {e}")
        return None