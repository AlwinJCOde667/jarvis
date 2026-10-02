import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL = "gemini-3.8-flash"


class VoiceRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {
        "status": "Jarvis voice server is running"
    }


@app.post("/ask")
def ask_jarvis(request: VoiceRequest):

    for attempt in range(3):

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=request.text
            )

            return {
                "reply": response.text
            }

        except Exception as e:

            if attempt == 2:
                return {
                    "reply": "Sorry, I am having trouble connecting to Gemini right now."
                }

            time.sleep(2)
