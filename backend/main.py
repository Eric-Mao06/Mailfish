import os
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure API keys
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Store personality prompts for each person
personality_prompts: Dict[str, str] = {}

class PersonRequest(BaseModel):
    name: str

class ChatRequest(BaseModel):
    name: str
    message: str

class PersonResponse(BaseModel):
    success: bool
    message: str

class ChatResponse(BaseModel):
    response: str

@app.options("/create-clone")
async def create_clone_options():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.post("/create-clone")
async def create_clone(request: PersonRequest) -> PersonResponse:
    if not PERPLEXITY_API_KEY or not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="API keys not configured")

    try:
        # Call Perplexity Sonar API for research
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [{
                        "role": "user",
                        "content": f"Please provide a detailed research report on {request.name}. Include their background, achievements, personality traits, and any notable information."
                    }]
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Perplexity API error: {response.text}"
                )
            
            research_data = response.json()
            research_text = research_data['choices'][0]['message']['content']

            # Generate personality prompt using Gemini
            personality_prompt = model.generate_content(
                f"""Based on this research about {request.name}, create a detailed system prompt that would help an AI model accurately simulate their personality, speech patterns, and knowledge:

                Research: {research_text}

                Create a system prompt that captures their:
                1. Personality traits and speaking style
                2. Knowledge domains and expertise
                3. Notable opinions and viewpoints
                4. Characteristic behaviors and mannerisms"""
            ).text

            # Store the personality prompt
            personality_prompts[request.name] = personality_prompt

            return JSONResponse(
                content={"success": True, "message": "Clone created successfully"},
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:3000",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Perplexity API timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating clone: {str(e)}"
        )

@app.options("/chat")
async def chat_options():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    if request.name not in personality_prompts:
        raise HTTPException(
            status_code=404,
            detail="Clone not found. Please create the clone first."
        )

    try:
        chat = model.start_chat(history=[])
        
        # Use the stored personality prompt
        system_prompt = personality_prompts[request.name]
        
        # Generate response using Gemini
        response = chat.send_message(
            f"""System: You are a simulation of {request.name}. Here is your personality and background information:
            {system_prompt}
            
            Remember to stay in character and respond as {request.name} would.
            
            User: {request.message}"""
        )

        return JSONResponse(
            content={"response": response.text},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000, log_level="debug")