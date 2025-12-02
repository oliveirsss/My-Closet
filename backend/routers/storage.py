from fastapi import APIRouter, Header, HTTPException
from database import supabase, get_user_from_token
from schemas import ImageUpload
from supabase import create_client
import base64
import uuid
import os

router = APIRouter()


@router.post("/upload-image")
def upload_image(data: ImageUpload, authorization: str = Header(None)):
    # 1. Validar Utilizador
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 2. Configurar Admin Temporário (para passar por cima das permissões)
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    url = os.environ.get("SUPABASE_URL")
    bucket_name = "make-1d4585bc-closet-images"

    if not service_key:
        raise HTTPException(status_code=500, detail="Erro de Configuração: SUPABASE_SERVICE_KEY em falta.")

    try:
        admin_supabase = create_client(url, service_key)

        # 3. Preparar Imagem
        if ';base64,' in data.image:
            _, imgstr = data.image.split(';base64,')
        else:
            imgstr = data.image

        image_bytes = base64.b64decode(imgstr)
        file_path = f"{user.user.id}/{uuid.uuid4()}_{data.fileName}"

        # 4. Upload (como Admin)
        admin_supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )

        # 5. Gerar Link (A CORREÇÃO ESTÁ AQUI: Usamos admin_supabase também)
        res = admin_supabase.storage.from_(bucket_name).create_signed_url(file_path, 31536000)  # Válido por 1 ano

        # O método create_signed_url pode retornar a URL diretamente ou num dict, dependendo da versão.
        # O Supabase-py geralmente retorna {'signedURL': '...'} ou string.
        # Vamos garantir que não falha:
        final_url = res if isinstance(res, str) else res.get("signedURL")

        return {"url": final_url, "path": file_path}

    except Exception as e:
        print(f"Erro upload imagem: {e}")
        # Se o erro for do Supabase, tentamos extrair a mensagem
        error_detail = str(e)
        if hasattr(e, 'message'):
            error_detail = e.message
        elif hasattr(e, 'json'):
            error_detail = str(e.json())

        raise HTTPException(status_code=500, detail=f"Image upload failed: {error_detail}")