import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

class PersonRequest(BaseModel):
    name: str

class PersonResponse(BaseModel):
    research: str
    personality_prompt: str

@app.post("/api/analyze-person")
async def analyze_person(request: PersonRequest) -> PersonResponse:
    if not PERPLEXITY_API_KEY or not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="API keys not configured")

    # Call Perplexity Sonar API with timeout and retries
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
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

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Request to Perplexity API timed out. Please try again."
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error calling Perplexity API: {str(e)}"
            )

        try:
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

            return PersonResponse(
                research=research_text,
                personality_prompt=personality_prompt
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating personality prompt: {str(e)}"
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)