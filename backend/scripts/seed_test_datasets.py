import os
import sys
import uuid
import requests
from dotenv import load_dotenv

# Ensure we can import from the main backend dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_user_from_token
from supabase import create_client

# Carregar variáveis de ambiente
load_dotenv()

def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("❌ ERRO: SUPABASE_URL ou SUPABASE_SERVICE_KEY não encontrada no .env")
        sys.exit(1)

    return create_client(url, key)

def get_or_create_user(admin_supabase, email, password, name):
    try:
        # Try to find by simulating a sign in, or just list users if possible
        # Actually admin API allows fetching all users or creating.
        # Let's try to create, if fails because exists, we'll try to find it.
        res = admin_supabase.auth.admin.list_users()
        users = res.users if hasattr(res, "users") else getattr(res, "users", [])
        for u in users:
            if u.email == email:
                print(f"✅ Found existing user {email} ({u.id})")
                return u.id
        res = admin_supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"name": name}
        })
        print(f"✅ Created user {email} ({res.user.id})")
        return res.user.id
    except Exception as e:
        print(f"❌ Failed to get or create user {email}: {e}")
        return None

def clear_user_closet(admin_supabase, user_id):
    try:
        admin_supabase.table("clothes").delete().eq("user_id", user_id).execute()
        print(f"✅ Cleared old closet for user {user_id}")
    except Exception as e:
        print(f"❌ Failed to clear closet for user {user_id}: {e}")

def seed_closet(admin_supabase, user_id, items):
    print(f"🔄 Preparing images for user {user_id}...")
    for item in items:
        item["user_id"] = user_id
        if "favorite" not in item:
            item["favorite"] = False
        if "status" not in item:
            item["status"] = "clean"
        if "is_public" not in item:
            item["is_public"] = True # Make it visible if you ever want public feed
            
    try:
        admin_supabase.table("clothes").insert(items).execute()
        print(f"✅ Injected {len(items)} items for user {user_id}")
    except Exception as e:
        print(f"❌ Failed to seed items for user {user_id}: {e}")


def main():
    print("🚀 Iniciando Seed de Test Datasets...")
    admin_supabase = get_admin_client()

    # Define Test User: Feminino/Casual + Vestidos
    female_user_id = "8c053623-d832-4723-8c13-d71e8a52e562"
    
    # Define Test User: Formal (Fatos, Galas)
    formal_user_id = "149c5245-7441-46fb-b9a3-92e00f05f314"

    if not female_user_id or not formal_user_id:
        print("❌ Abortando devido a erros nas contas.")
        sys.exit(1)

    clear_user_closet(admin_supabase, female_user_id)
    clear_user_closet(admin_supabase, formal_user_id)

    female_closet = [
        # TOPS (Layer 1)
        {
            "name": "Blusa Seda Branca", "type": "shirt", "layer": 1,
            "materials": ["silk"], "weight": 0.2, "temp_min": 15, "temp_max": 35,
            "seasons": ["spring", "summer"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/marni-red-&-black-suit/2.webp",
            "waterproof": False, "windproof": False
        },
        {
            "name": "Crop Top Bordo", "type": "shirt", "layer": 1,
            "materials": ["cotton"], "weight": 0.1, "temp_min": 20, "temp_max": 40,
            "seasons": ["summer"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/marni-red-&-black-suit/1.webp",
            "waterproof": False, "windproof": False
        },
        # BOTTOMS (Layer 2 natively mapped or Layer 1 bottom)
        {
            "name": "Saia Xadrez Curta", "type": "skirt", "layer": 2, # treating skirts/pants mostly as layer 2 visually
            "materials": ["polyester"], "weight": 0.3, "temp_min": 15, "temp_max": 35,
            "seasons": ["spring", "summer"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/marni-red-&-black-suit/3.webp",
            "waterproof": False, "windproof": False
        },
        {
            "name": "Calças Gangas Clássicas", "type": "pants", "layer": 2,
            "materials": ["linen"], "weight": 0.4, "temp_min": 15, "temp_max": 35,
            "seasons": ["spring", "summer"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/marni-red-&-black-suit/4.webp",
            "waterproof": False, "windproof": False
        },
        # DRESSES
        {
            "name": "Vestido Vermelho Elegante", "type": "dress", "layer": 1,
            "materials": ["cotton", "viscose"], "weight": 0.3, "temp_min": 22, "temp_max": 40,
            "seasons": ["summer"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/dress-pea/thumbnail.webp",
            "waterproof": False, "windproof": False
        },
        # OUTERWEAR
        {
            "name": "Casaco Impermeável Amarelo", "type": "jacket", "layer": 3,
            "materials": ["nylon"], "weight": 0.4, "temp_min": 10, "temp_max": 25,
            "seasons": ["spring", "fall"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/dress-pea/1.webp",
            "waterproof": True, "windproof": True
        },
        {
            "name": "Casaco Pele Preto", "type": "jacket", "layer": 3,
            "materials": ["cotton blend"], "weight": 1.2, "temp_min": 5, "temp_max": 18,
            "seasons": ["fall", "winter", "spring"], "image": "https://cdn.dummyjson.com/product-images/womens-dresses/dress-pea/2.webp",
            "waterproof": True, "windproof": True
        },
        # SHOES
        {
            "name": "Salto Alto Vermelho", "type": "shoes", "layer": 3,
            "materials": ["leather"], "weight": 0.5, "temp_min": 10, "temp_max": 35,
            "seasons": ["spring", "summer", "fall", "winter"], "image": "https://cdn.dummyjson.com/product-images/womens-shoes/chappal-gold/1.webp",
            "waterproof": False, "windproof": False
        },
        {
            "name": "Sandálias Práticas", "type": "shoes", "layer": 3,
            "materials": ["leather"], "weight": 0.2, "temp_min": 20, "temp_max": 40,
            "seasons": ["summer"], "image": "https://cdn.dummyjson.com/product-images/womens-shoes/chappal-gold/thumbnail.webp",
            "waterproof": False, "windproof": False
        }
    ]

    formal_closet = [
        # TOPS
        {
            "name": "T-Shirt Básica Branca", "type": "shirt", "layer": 1,
            "materials": ["cotton"], "weight": 0.3, "temp_min": 5, "temp_max": 30,
            "seasons": ["spring", "summer", "fall", "winter"], "image": "https://cdn.dummyjson.com/product-images/mens-shirts/blue-tshirt/1.webp",
            "waterproof": False, "windproof": False
        },
        {
            "name": "T-shirt Casual Azul", "type": "shirt", "layer": 1,
            "materials": ["cotton"], "weight": 0.3, "temp_min": 5, "temp_max": 30,
            "seasons": ["spring", "summer", "fall", "winter"], "image": "https://cdn.dummyjson.com/product-images/mens-shirts/blue-tshirt/2.webp",
            "waterproof": False, "windproof": False
        },
        # BOTTOMS
        {
            "name": "Calças de Fato Cinzentas", "type": "pants", "layer": 2,
            "materials": ["wool"], "weight": 0.6, "temp_min": -5, "temp_max": 25,
            "seasons": ["fall", "winter", "spring"], "image": "https://cdn.dummyjson.com/product-images/mens-shirts/blue-tshirt/3.webp",
            "waterproof": False, "windproof": False
        },
        # INSULATION
        {
            "name": "Casaco Verde Militar", "type": "jacket", "layer": 3,
            "materials": ["cotton"], "weight": 0.9, "temp_min": 5, "temp_max": 22,
            "seasons": ["fall", "winter", "spring"], "image": "https://cdn.dummyjson.com/product-images/mens-shirts/man-plaid-shirt/1.webp",
            "waterproof": False, "windproof": False
        },
        # SHOES
        {
            "name": "Sapatos Oxford Clássicos", "type": "shoes", "layer": 3,
            "materials": ["leather"], "weight": 1.2, "temp_min": -10, "temp_max": 30,
            "seasons": ["spring", "summer", "fall", "winter"], "image": "https://cdn.dummyjson.com/product-images/mens-shoes/sneakers-light-green/thumbnail.webp",
            "waterproof": True, "windproof": True
        },
        {
            "name": "Sapatos Vintage Castanhos", "type": "shoes", "layer": 3,
            "materials": ["leather"], "weight": 0.9, "temp_min": 5, "temp_max": 25,
            "seasons": ["spring", "fall"], "image": "https://cdn.dummyjson.com/product-images/mens-shoes/canvas-shoes/thumbnail.webp",
            "waterproof": False, "windproof": False
        }
    ]

    seed_closet(admin_supabase, female_user_id, female_closet)
    seed_closet(admin_supabase, formal_user_id, formal_closet)
    
    print("🎉 Concluído com sucesso! Pode entrar nas contas com as credenciais acima para testar a IA.")

if __name__ == "__main__":
    main()
