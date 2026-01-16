from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from database import get_user_from_token
from supabase import create_client
import uuid
import os

router = APIRouter()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), authorization: str = Header(None)):
    # 1. Validar Utilizador
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 2. Configurar Admin
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    url = os.environ.get("SUPABASE_URL")
    bucket_name = "make-1d4585bc-closet-images"

    if not service_key:
        raise HTTPException(status_code=500, detail="Erro de Configuração: SUPABASE_SERVICE_KEY em falta.")

    try:
        admin_supabase = create_client(url, service_key)

        # 3. Preparar Ficheiro
        file_ext = file.filename.split(".")[-1]
        file_path = f"{user.user.id}/{uuid.uuid4()}.{file_ext}"

        # Ler o conteúdo do ficheiro
        file_content = await file.read()

        # 4. Upload (como Admin)
        admin_supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )

        # 5. Gerar URL (Signed URL para garantir acesso mesmo se o bucket for privado)
        # 10 anos de validade
        response_signed = admin_supabase.storage.from_(bucket_name).create_signed_url(file_path, 315360000)
        
        # O método create_signed_url retorna um dict ou string dependendo da versão, 
        # mas normalmente é um dict com 'signedURL' ou 'signedUrl'.
        # Vamos verificar o retorno. Na lib 'supabase' python, create_signed_url retorna um dict: {'signedURL': '...'}
        
        # Ajuste para garantir robustez
        if isinstance(response_signed, dict) and 'signedURL' in response_signed:
            public_url = response_signed['signedURL']
        else:
             # Fallback ou se a versão da lib for diferente, tenta assumir que é directo ou outro formato
             # Mas assumindo a versão standard do supabase-py
             public_url = response_signed.get('signedURL') if isinstance(response_signed, dict) else str(response_signed)

        return {"url": public_url}

    except Exception as e:
        print(f"Erro upload imagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))