import json
import shutil
import os
import joblib
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from src.train import train_model

app = FastAPI()
models = {}
MODEL_PATH = "models/latest_model.pkl"

def convert_to_jsonl(input_path):
    """Converts a standard JSON list to JSON Lines to save RAM."""
    output_path = input_path + ".jsonl"
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in data:
            f.write(json.dumps(entry) + '\n')
    return output_path

def background_training(file_path: str):
    try:
        # 1. Convert to RAM-friendly format
        print("🔄 Converting file to 8GB-safe format...")
        safe_path = convert_to_jsonl(file_path)
        
        # 2. Train using the chunked method
        success = train_model(safe_path, MODEL_PATH)
        
        if success:
            models["latest"] = joblib.load(MODEL_PATH)
            print("🚀 SUCCESS: API is now LIVE with your model.")
            
    except Exception as e:
        print(f"❌ BACKGROUND ERROR: {e}")

@app.post("/upload-and-train")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    os.makedirs("data", exist_ok=True)
    path = f"data/{file.filename}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(background_training, path)
    return {"status": "Converting and Training... Check PowerShell!"}

@app.get("/")
async def status():
    return {"model_ready": "latest" in models}

from pydantic import BaseModel
from typing import List

# 1. Define what the input looks like
class PredictionRequest(BaseModel):
    features: List[float]

# 2. Create the Predict Button
@app.post("/predict")
async def predict(request: PredictionRequest):
    if "latest" not in models:
        return {"error": "Model not loaded. Train first!"}
    
    # AI calculation
    prediction = models["latest"].predict([request.features])
    
    return {
        "prediction": int(prediction[0]),
        "status": "Success"
    }
