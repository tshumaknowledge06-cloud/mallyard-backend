import os
import uuid
import shutil
from fastapi import UploadFile


def save_upload_file(file: UploadFile, folder: str, prefix: str):
    os.makedirs(folder, exist_ok=True)

    # ✅ Clean filename (avoid spaces & weird chars)
    original_name = file.filename.replace(" ", "_")

    # ✅ Unique filename
    filename = f"{prefix}_{uuid.uuid4().hex}_{original_name}"

    file_path = os.path.join(folder, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return filename