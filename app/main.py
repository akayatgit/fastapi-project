from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from supabase import create_client, Client
from pydantic import BaseModel
import random
import json
from app.core.config import settings

app = FastAPI(
    title="Spotive API",
    description="AI-Powered Event Discovery API for Bangalore",
    version="0.1.0 (MVP)"
)

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Initialize the LLM model based on provider (Ollama for local, OpenAI for production)
def get_llm_model():
    """Get LLM model based on environment configuration"""
    if settings.LLM_PROVIDER.lower() == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")
        return ChatOpenAI(
            model=settings.LLM_MODEL if settings.LLM_MODEL != "gemma3" else "gpt-3.5-turbo",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7
        )
    else:
        # Default to Ollama for local development
        return ChatOllama(model=settings.LLM_MODEL, keep_alive="1h")

try:
    model = get_llm_model()
    llm_available = True
except Exception as e:
    print(f"Warning: LLM initialization failed: {e}")
    model = None
    llm_available = False

# Create the prompt template for conversational event descriptions
event_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Spotive, a friendly AI event discovery assistant talking to users over the phone in Bangalore, India. 
    
    You'll be given details about an actual event happening in Bangalore. Your job is to present it in an exciting, conversational way.
    
    IMPORTANT: Respond in exactly 20 words, talking naturally like you're chatting with a friend over the phone.
    - Line 1: Introduce the event/place in an exciting way
    - Line 2: Share what makes it special or what they'll experience
    - Line 3: Mention location, timing, and price in a casual way
    
    Speak like a local Bangalore person. Be enthusiastic but natural!
    Don't use JSON or structured data - just talk like a normal person would."""),
    ("human", """Tell me about this event in a friendly, conversational way:
    
Event Name: {name}
Category: {category}
Description: {description}
Location: {location}
Date: {date}
Time: {time}
Price: {price}""")
])

# LLM prompt to map interests to categories
category_mapping_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent category mapping system for Spotive event discovery.

Your job is to map user interests to our predefined event categories.

**Predefined Categories (ONLY use these):**
- concert (music events, live performances, DJ nights, music festivals)
- sports (marathons, cricket, football, fitness events, yoga)
- outdoor (trekking, hiking, nature activities, adventure sports)
- food (food festivals, buffet events, culinary experiences)
- spiritual (religious events, meditation, temple visits, spiritual gatherings)
- cultural (art exhibitions, theater, dance performances, traditional events)
- kids (children activities, family events, kids workshops)
- entertainment (comedy shows, standup, movies, fun activities)

**Instructions:**
1. Analyze the user's interests
2. Map them to the most relevant categories from the list above
3. Return ONLY a JSON array of matching categories
4. Format: ["category1", "category2", ...]
5. Include multiple categories if interests span different areas
6. If uncertain, include related categories

**Examples:**
- "music, dancing" → ["concert", "entertainment"]
- "family fun" → ["kids", "entertainment"]
- "adventure, nature" → ["outdoor", "sports"]
- "food, traditional" → ["food", "cultural"]
- "fitness, wellness" → ["sports", "spiritual"]
"""),
    ("human", "User interests: {interests}\n\nReturn ONLY the JSON array of matching categories:")
])

# Pydantic model for interests request body
class InterestsRequest(BaseModel):
    interests: str  # Comma-separated interests
    
    class Config:
        json_schema_extra = {
            "example": {
                "interests": "music, outdoor, adventure"
            }
        }

@app.get("/")
def read_root():
    """
    Root endpoint - API health check
    """
    return {
        "message": "Welcome to Spotive API!",
        "status": "active",
        "version": "0.1.0 (MVP)",
        "description": "AI-Powered Event Discovery for Bangalore",
        "environment": {
            "is_vercel": settings.IS_VERCEL,
            "is_production": settings.IS_PRODUCTION,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "llm_available": llm_available
        },
        "note": "Connected to Supabase with LLM-powered conversational responses" if llm_available else "Connected to Supabase (LLM unavailable)"
    }

@app.post("/api/event/by-interests")
def get_event_by_interests(request: InterestsRequest):
    """
    Get events based on user interests. The LLM maps interests to categories and queries matching events.
    
    Request body:
    - interests: Comma-separated interests (e.g., "music, outdoor, adventure")
    
    The system will:
    1. Use AI to map interests to event categories
    2. Query events matching those categories
    3. Return a random event with conversational description
    """
    try:
        # Predefined categories
        valid_categories = ["concert", "sports", "outdoor", "food", "spiritual", "cultural", "kids", "entertainment"]
        
        # Step 1: Use LLM to map interests to categories
        if llm_available and model:
            try:
                mapping_chain = category_mapping_prompt | model
                mapping_response = mapping_chain.invoke({"interests": request.interests})
                
                # Parse the LLM response to get categories
                try:
                    categories = json.loads(mapping_response.content.strip())
                    if not isinstance(categories, list):
                        # Fallback: use all categories
                        categories = valid_categories
                    else:
                        # Filter to only valid categories
                        categories = [cat.lower() for cat in categories if cat.lower() in valid_categories]
                        if not categories:
                            categories = valid_categories
                except json.JSONDecodeError:
                    # If parsing fails, use all categories
                    categories = valid_categories
            except Exception as e:
                print(f"Category mapping failed: {e}")
                # Fallback: use all categories
                categories = valid_categories
        else:
            # If LLM not available, use all categories
            categories = valid_categories
        
        # Step 2: Query Supabase for events matching any of the categories
        # Build OR query for multiple categories
        events = []
        for category in categories:
            response = supabase.table('events').select("*").eq('category', category).execute()
            if response.data:
                events.extend(response.data)
        
        if not events or len(events) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No events found matching interests: {request.interests}",
                    "mapped_categories": categories
                }
            )
        
        # Step 3: Pick a random event from all matching events
        event = random.choice(events)
        
        # Step 4: Generate conversational description if LLM is available
        if llm_available and model:
            try:
                chain = event_prompt | model
                
                llm_response = chain.invoke({
                    "name": event.get("name", "Unknown Event"),
                    "category": event.get("category", "event"),
                    "description": event.get("description", "An exciting event"),
                    "location": event.get("location", "Bangalore"),
                    "date": event.get("date", "Soon"),
                    "time": event.get("time", "TBA"),
                    "price": event.get("price", "Contact organizer")
                })
                suggestion = llm_response.content
            except Exception as llm_error:
                print(f"LLM generation failed: {llm_error}")
                suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}! {event.get('description', 'An exciting event.')} It's on {event.get('date', 'soon')} at {event.get('time', 'TBA')}."
        else:
            suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}! {event.get('description', 'An exciting event.')} It's on {event.get('date', 'soon')} at {event.get('time', 'TBA')}."
        
        # Return the conversational response
        return JSONResponse(content={
            "success": True,
            "interests": request.interests,
            "mapped_categories": categories,
            "total_matching_events": len(events),
            "suggestion": suggestion,
            "event_details": {
                "id": event.get("id"),
                "name": event.get("name"),
                "category": event.get("category"),
                "location": event.get("location"),
                "date": event.get("date"),
                "time": event.get("time"),
                "price": event.get("price"),
                "image_url": event.get("image_url"),
                "booking_link": event.get("booking_link")
            },
            "source": "Supabase",
            "ai_generated": llm_available
        })
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to fetch events from Supabase"
            }
        )