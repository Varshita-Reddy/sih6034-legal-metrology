from fastapi import FastAPI, UploadFile, File
import os
import shutil

app = FastAPI()

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.get("/")
def home():
    return {"message": "Legal Metrology Backend is running!"}


@app.post("/scan")
async def scan_image(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "Image uploaded successfully!",
        "filename": file.filename,
        "path": file_path
    }