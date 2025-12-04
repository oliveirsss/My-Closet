import os
import random
from dotenv import load_dotenv
from supabase import create_client

# 1. Carregar variáveis de ambiente
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("❌ Erro: SUPABASE_URL ou SUPABASE_SERVICE_KEY não encontrados no .env")
    exit()

# Usar cliente Admin para poder inserir em nome de qualquer user
supabase = create_client(url, key)

print("🚀 A iniciar a geração de dados...")

# 2. Buscar utilizadores existentes (para atribuir a roupa a pessoas reais)
try:
    users_response = supabase.auth.admin.list_users()
    users = users_response
    if not users:
        print("❌ Erro: Não tens utilizadores criados. Cria uma conta no site primeiro.")
        exit()
    user_ids = [u.id for u in users]
    print(f"✅ Encontrados {len(user_ids)} utilizadores.")
except Exception as e:
    print(f"❌ Erro ao buscar users: {e}")
    exit()

# 3. Dados para gerar aleatoriamente
types = ["Casaco", "T-shirt", "Calças", "Camisola", "Vestido", "Calções", "Camisa", "Saia"]
brands = ["Nike", "Adidas", "Zara", "H&M", "North Face", "Patagonia", "Levi's", "Uniqlo", "Bershka"]
materials_list = ["Algodão", "Poliéster", "Lã", "Linho", "Gore-Tex", "Ganga", "Seda", "Elastano"]
weather_conditions = ["Sunny", "Rainy", "Windy", "Cloudy"]

# URLs de imagens reais do Unsplash para ficar bonito
images = [
    "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400",  # Casaco
    "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400",  # Camisola
    "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400",  # T-shirt
    "https://images.unsplash.com/photo-1542272617-08f086302542?w=400",  # Calças
    "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400",  # Casaco
    "https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400",  # Shirt
    "https://images.unsplash.com/photo-1582552966795-79d50040e901?w=400",  # Shoes/Pants
    "https://images.unsplash.com/photo-1603252109303-2751440ee43d?w=400",  # Coat
    "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=400"  # T-shirt
]

items_to_create = []

# 4. Gerar 30 Peças
for i in range(30):
    item_type = random.choice(types)
    layer = 1
    if item_type in ["Casaco", "Blusão"]:
        layer = 3
    elif item_type in ["Camisola", "Camisa"]:
        layer = 2

    temp_min = random.randint(-5, 15)

    # Gerar 1 ou 2 materiais
    num_materials = random.randint(1, 2)
    item_materials = random.sample(materials_list, num_materials)

    item = {
        "user_id": random.choice(user_ids),  # Atribui a um user aleatório
        "name": f"{item_type} {random.choice(brands)}",
        "brand": random.choice(brands),
        "size": random.choice(["S", "M", "L", "XL"]),
        "type": item_type,
        "layer": layer,
        "materials": item_materials,
        "weight": random.randint(100, 800),
        "temp_min": temp_min,
        "temp_max": temp_min + 10,
        "waterproof": random.choice([True, False]),
        "windproof": random.choice([True, False]),
        "seasons": random.sample(["Inverno", "Outono", "Primavera", "Verão"], random.randint(1, 2)),
        "image": random.choice(images),
        "status": random.choice(["clean", "dirty"]),
        "favorite": random.choice([True, False]),
        "is_public": True  # IMPORTANTE: A maioria pública
    }
    items_to_create.append(item)

# 5. Inserir na Base de Dados
try:
    data = supabase.table("clothes").insert(items_to_create).execute()
    print(f"🎉 Sucesso! Foram adicionadas {len(items_to_create)} peças novas à base de dados.")
except Exception as e:
    print(f"❌ Erro ao inserir: {e}")