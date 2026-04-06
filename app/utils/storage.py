import requests
import os
import uuid

def upload_file_to_supabase(file):
    file_id = str(uuid.uuid4())
    filename = f"{file_id}-{file.filename}"

    url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/{os.getenv('SUPABASE_BUCKET')}/{filename}"

    headers = {
        "apikey": os.getenv("SUPABASE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
        "Content-Type": file.content_type,
    }

    response = requests.post(
        url,
        headers=headers,
        data=file.file.read()
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"Upload failed: {response.text}")

    public_url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{os.getenv('SUPABASE_BUCKET')}/{filename}"

    return public_url