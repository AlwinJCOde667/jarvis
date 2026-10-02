import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

    def generate():

        response = client.models.generate_content_stream(
            model=MODEL,
            contents=(
                "You are Jarvis, a fast voice assistant. "
                "Reply naturally and briefly. "
                "For voice responses, use no more than 2 short sentences. "
                "User says: " + request.text
            )
        )

        for chunk in response:

            if chunk.text:
                yield chunk.text

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
