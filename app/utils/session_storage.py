import os
import json
import boto3
from datetime import datetime
from typing import Dict, Any

import streamlit as st

def save_s3_object(s3_client, bucket: str, key: str, data: Any):
    """Auxiliar para salvar JSON no S3"""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2, ensure_ascii=False),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Erro ao salvar no S3 ({key}): {e}")

def save_session_data(state: Dict[str, Any], base_dir: str = "conversation_logs"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    
    try:
        secrets = st.secrets
        bucket_name = secrets.get("S3_BUCKET_NAME")
        aws_region = secrets.get("AWS_REGION", "us-east-2")
        aws_access_key = secrets.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = secrets.get("AWS_SECRET_ACCESS_KEY")
    except Exception:
        bucket_name = None
        aws_region = os.getenv("AWS_REGION", "us-east-2")
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
    
    if bucket_name:
        # --- MODO S3 ---
        s3_base_path = f"session_{timestamp}"
        
        try:
            # Monta kwargs para o boto3
            boto_kwargs = {
                'service_name': 's3',
                'region_name': aws_region
            }
            
            # Se credenciais forem fornecidas explicitamente (comum em secrets.toml), usa-as
            if aws_access_key and aws_secret_key:
                boto_kwargs['aws_access_key_id'] = aws_access_key
                boto_kwargs['aws_secret_access_key'] = aws_secret_key
            
            # Inicializa cliente S3
            s3 = boto3.client(**boto_kwargs)
            
            print(f"Salvando logs no S3 Bucket: {bucket_name}, Pasta: {s3_base_path}")

            # 1. Conversa
            save_s3_object(s3, bucket_name, f"{s3_base_path}/conversation.json", state.get("context_messages", []))
            
            # 2. JSON final
            save_s3_object(s3, bucket_name, f"{s3_base_path}/finaljson.json", state.get("final_json"))
            
            # 3. Logs
            save_s3_object(s3, bucket_name, f"{s3_base_path}/agent_logs.json", state.get("logs", []))

            return f"s3://{bucket_name}/{s3_base_path}"

        except Exception as e:
            print(f"Falha ao salvar no S3, tentando backup local. Erro: {e}")
            # Fallback para local
            pass

    # --- MODO LOCAL (Padrão ou Fallback) ---
    session_dir = os.path.join(base_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)

    # 1. Conversa
    with open(os.path.join(session_dir, "conversation.json"), "w", encoding="utf-8") as f:
        json.dump(state.get("context_messages", []), f, indent=2, ensure_ascii=False)

    # 2. JSON final
    with open(os.path.join(session_dir, "finaljson.json"), "w", encoding="utf-8") as f:
        json.dump(state.get("final_json"), f, indent=2, ensure_ascii=False)

    # 3. Logs
    with open(os.path.join(session_dir, "agent_logs.json"), "w", encoding="utf-8") as f:
        json.dump(state.get("logs", []), f, indent=2, ensure_ascii=False)

    return session_dir