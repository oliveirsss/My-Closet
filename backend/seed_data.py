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
# Organized by layer for better distribution
layer1_types = ["T-shirt", "Camiseta", "Regata", "Top"]  # Base layer
layer2_types = ["Camisola", "Camisa", "Sweater", "Cardigan", "Pullover", "Hoodie"]  # Insulation
layer3_types_jackets = ["Casaco", "Jacket", "Blusão", "Coat", "Parka", "Blazer"]  # Outer layer - jackets
layer3_types_shoes = ["Calçado", "Sapatilhas", "Sapatos", "Sneakers", "Boots"]  # Outer layer - shoes
layer3_types_accessories = ["Chapéu", "Hat", "Boné", "Cap", "Gorro", "Beanie", "Luvas", "Gloves"]  # Outer layer - accessories
layer3_types = layer3_types_jackets + layer3_types_shoes + layer3_types_accessories
all_types = layer1_types + layer2_types + layer3_types

brands = ["Nike", "Adidas", "Zara", "H&M", "North Face", "Patagonia", "Levi's", "Uniqlo", "Bershka", "Vans", "Converse", "Pull&Bear", "Stradivarius"]
materials_list = ["Algodão", "Poliéster", "Lã", "Linho", "Gore-Tex", "Ganga", "Seda", "Elastano", "Poliéster", "Malha"]

# URLs de imagens reais do Unsplash para ficar bonito - organized by type
layer1_images = [
    "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400",  # T-shirt
    "https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=400",  # T-shirt
    "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=400",  # T-shirt
    "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400",  # T-shirt
]
layer2_images = [
    "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400",  # Camisola/Sweater
    "https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400",  # Shirt
    "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=400",  # Hoodie
    "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400",  # Cardigan
]
layer3_images = [
    "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400",  # Casaco/Jacket
    "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400",  # Casaco
    "https://images.unsplash.com/photo-1603252109303-2751440ee43d?w=400",  # Coat
    "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?w=400",  # Parka
]

items_to_create = []

# 4. Gerar mais peças (60 items) com distribuição balanceada por layer
for i in range(60):
    # Distribute: 35% layer 1, 25% layer 2, 40% layer 3 (more outer items for variety)
    rand = random.random()
    if rand < 0.35:
        layer = 1
        item_type = random.choice(layer1_types)
        images_pool = layer1_images
        temp_min = random.randint(15, 30)  # Warmer items for base layer
        temp_max = temp_min + 10
    elif rand < 0.60:
        layer = 2
        item_type = random.choice(layer2_types)
        images_pool = layer2_images
        temp_min = random.randint(5, 20)  # Moderate temps for insulation
        temp_max = temp_min + 12
    else:
        layer = 3
        # For layer 3, distribute: 40% jackets, 40% shoes, 20% accessories
        layer3_rand = random.random()
        if layer3_rand < 0.4:
            item_type = random.choice(layer3_types_jackets)
            images_pool = layer3_images
            temp_min = random.randint(-5, 15)  # Colder temps for jackets
            temp_max = temp_min + 15
            waterproof = random.random() < 0.5  # Jackets more likely waterproof
            windproof = random.random() < 0.6
        elif layer3_rand < 0.8:
            item_type = random.choice(layer3_types_shoes)
            images_pool = layer3_images  # Could add shoe images later
            temp_min = random.randint(0, 25)  # Shoes work in wider range
            temp_max = temp_min + 20
            waterproof = random.random() < 0.3  # Some shoes waterproof
            windproof = False
        else:
            item_type = random.choice(layer3_types_accessories)
            images_pool = layer3_images  # Could add accessory images later
            temp_min = random.randint(-10, 20)  # Accessories for cold weather
            temp_max = temp_min + 25
            waterproof = random.random() < 0.2
            windproof = random.random() < 0.3

    # Gerar 1 ou 2 materiais
    num_materials = random.randint(1, 2)
    item_materials = random.sample(materials_list, num_materials)

    # Determine seasons based on temperature range
    seasons = []
    if temp_min < 10:
        seasons.append("Inverno")
    if temp_min < 15:
        seasons.append("Outono")
    if temp_max > 15:
        seasons.append("Primavera")
    if temp_max > 20:
        seasons.append("Verão")
    if not seasons:
        seasons = ["Primavera", "Outono"]

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
        "temp_max": temp_max,
        "waterproof": waterproof,
        "windproof": windproof,
        "seasons": seasons[:2],  # Max 2 seasons
        "image": random.choice(images_pool),
        "status": "clean" if random.random() < 0.8 else "dirty",  # 80% clean
        "favorite": random.random() < 0.2,  # 20% favorites
        "is_public": True  # IMPORTANTE: A maioria pública
    }
    items_to_create.append(item)

# 5. Inserir na Base de Dados
try:
    data = supabase.table("clothes").insert(items_to_create).execute()
    print(f"🎉 Sucesso! Foram adicionadas {len(items_to_create)} peças novas à base de dados.")
except Exception as e:
    print(f"❌ Erro ao inserir: {e}")