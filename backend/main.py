from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Legal Metrology Backend is running!"}
