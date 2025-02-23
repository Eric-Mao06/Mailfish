import os
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from services.video_finder import VideoFinder
from services.process_video import VideoProcessor
from services.voice_generator import VoiceGenerator

load_dotenv()

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5000",
    "https://frontend-production-f346.up.railway.app"
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

# Store personality prompts and voice IDs for each person
personality_prompts: Dict[str, str] = {}
voice_ids: Dict[str, str] = {}

class PersonRequest(BaseModel):
    name: str

class ChatRequest(BaseModel):
    name: str
    message: str

class TextToSpeechRequest(BaseModel):
    name: str
    text: str

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

                {research_text}

                Format the prompt to start with: 'You are {request.name}...'"""
            ).text

            # Store personality prompt
            personality_prompts[request.name] = personality_prompt

            # Initialize voice cloning services
            video_finder = VideoFinder()
            video_processor = VideoProcessor()
            voice_generator = VoiceGenerator()

            # Find videos of the person speaking
            profile_info = {"name": request.name, "bio": research_text}
            video_urls = video_finder.find_videos(profile_info)

            if not video_urls:
                return PersonResponse(
                    success=True,
                    message=f"Created AI clone for {request.name}, but couldn't find suitable videos for voice cloning"
                )

            # Process videos to extract audio
            audio_path = video_processor.process_videos(video_urls, profile_info)

            if not audio_path:
                return PersonResponse(
                    success=True,
                    message=f"Created AI clone for {request.name}, but couldn't process videos for voice cloning"
                )

            # Generate voice clone
            voice_result = voice_generator.generate_voice_clone(
                audio_path=audio_path,
                voice_name=request.name,
                description=f"AI voice clone of {request.name}"
            )

            if voice_result and 'voice_id' in voice_result:
                voice_ids[request.name] = voice_result['voice_id']
                return PersonResponse(
                    success=True,
                    message=f"Successfully created AI clone and voice clone for {request.name}"
                )
            else:
                return PersonResponse(
                    success=True,
                    message=f"Created AI clone for {request.name}, but voice cloning failed"
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.options("/text-to-speech")
async def text_to_speech_options():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.post("/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    try:
        # Get voice ID for the requested name
        if request.name not in voice_ids:
            raise HTTPException(
                status_code=404,
                detail=f"No voice found for {request.name}. Please create a clone first."
            )
        
        voice_id = voice_ids[request.name]
        
        # Initialize voice generator
        voice_generator = VoiceGenerator()
        
        # Generate speech
        audio_data = voice_generator.text_to_speech(voice_id, request.text)
        
        if not audio_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate speech"
            )
        
        # Return audio data with appropriate headers
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")