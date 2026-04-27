"""
Script para fazer download do Fashion Product Images Dataset do Kaggle.
Usa o novo sistema de tokens do Kaggle (KAGGLE_API_TOKEN).
"""
import os
import sys

# Define o token de autenticação
os.environ["KAGGLE_API_TOKEN"] = "KGAT_a4bbc54715f9d23355b42c1179217d37"

import kagglehub

print("=" * 60)
print("A fazer download do Fashion Product Images Dataset...")
print("=" * 60)

try:
    # Dataset: Fashion Product Images Dataset
    # https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
    path = kagglehub.dataset_download("paramaggarwal/fashion-product-images-dataset")
    print(f"\n✅ Download concluído!")
    print(f"📁 Dataset guardado em: {path}")
    
    # Mostrar estrutura do dataset
    print("\n📂 Estrutura do dataset:")
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        if level < 2:  # Só mostrar 2 níveis de profundidade
            subindent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # Primeiros 5 ficheiros
                print(f'{subindent}{file}')
            if len(files) > 5:
                print(f'{subindent}... e mais {len(files) - 5} ficheiros')
                
except Exception as e:
    print(f"\n❌ Erro durante o download: {e}")
    print("\nTenta verificar:")
    print("  1. Se o token está correto")
    print("  2. Se aceitaste as regras do dataset no Kaggle")
    print("  3. O link exato do dataset")
    sys.exit(1)
