
import os
import uuid
import shutil
import requests
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing analysis logic from src
from src.analysis.ifake_tools import predict_ifake_forgery
from src.analysis.ela import generate_ela, ela_score

app = FastAPI(title="Kavach AI — Batch Processing")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
IFAKE_IMG_WEIGHTS = Path("weights/proposed_ela_50_casia_fidac.h5")

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in environment variables.")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[dict] = None

class BatchResult(BaseModel):
    file_id: str
    filename: str
    trust_score: int
    risk: str  # safe, medium, high
    status: str = "completed"

def get_risk_level(score: int) -> str:
    if score >= 80: return "safe"
    if score >= 50: return "medium"
    return "high"

def process_file(file_path: Path) -> dict:
    """Core logic to analyze a document using existing modules."""
    # Try IFAKE first
    if IFAKE_IMG_WEIGHTS.exists():
        res = predict_ifake_forgery(file_path, IFAKE_IMG_WEIGHTS)
        if "error" not in res:
            confidence = res["confidence"]
            score = int(confidence * 100) if res["verdict"] == "Authentic" else int((1 - confidence) * 100)
            return {"trust_score": score, "risk": get_risk_level(score)}
    
    # Fallback to ELA
    try:
        ela_img = generate_ela(file_path)
        e_score = ela_score(ela_img)
        # Heuristic: map ELA intensity to 0-100 trust
        trust = max(0, min(100, int(100 - (e_score * 1000))))
        return {"trust_score": trust, "risk": get_risk_level(trust)}
    except Exception:
        return {"trust_score": 50, "risk": "medium"}

@app.post("/api/batch", response_model=List[BatchResult])
async def batch_process(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix or ".png"
        save_path = UPLOAD_DIR / f"{file_id}{ext}"
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        analysis = process_file(save_path)
        results.append(BatchResult(
            file_id=file_id,
            filename=file.filename,
            trust_score=analysis["trust_score"],
            risk=analysis["risk"]
        ))
    return results

@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    """Handle chat messages for Kavach AI Assistant."""
    system_prompt = (
        "You are Kavach AI Assistant, a fraud detection expert. Your job is to explain document verification results clearly and help users understand risks. "
        "Always base your answers on the provided analysis data. Be concise and professional."
    )
    
    if request.context:
        system_prompt += f"\n\nCurrent Context:\nTrust Score: {request.context.get('trust_score')}%\nRisk Level: {request.context.get('risk')}\nFindings: {request.context.get('findings')}"

    # Prepare payload for Groq
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 1024
    }

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured. Please check your .env file.")

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return {"content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API Error: {str(e)}")

# Serve Frontend (to be built into 'frontend/out')
if os.path.exists("frontend/out"):
    app.mount("/", StaticFiles(directory="frontend/out", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
