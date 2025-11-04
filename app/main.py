from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from supabase import create_client, Client
from pydantic import BaseModel
import random
import json
from typing import List, Optional
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

# MCP-style filtering prompt for user preferences
mcp_filter_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent event filtering system using MCP (Model Context Protocol).
    
    Given a list of events and user preferences, you need to filter and rank the events based on how well they match the user's preferences.
    
    User preferences might include:
    - Event types/categories (e.g., "music", "outdoor", "family-friendly", "spiritual")
    - Interests (e.g., "adventure", "culture", "food", "relaxation")
    - Activity level (e.g., "active", "relaxing", "social")
    - Budget preferences (e.g., "free", "cheap", "moderate", "premium")
    - Any other contextual preferences
    
    Analyze each event and return ONLY a JSON array of event IDs that match the preferences, ranked from best to worst match.
    Format: ["id1", "id2", "id3", ...]
    
    If no events match well, return an empty array: []
    
    Be intelligent about matching - for example:
    - "family" or "kids" preferences should match kids-friendly events
    - "adventure" could match outdoor or sports events
    - "cultural" or "traditional" should match cultural and spiritual events
    - "music" or "entertainment" matches concerts and entertainment events
    """),
    ("human", """User Preferences: {preferences}

Available Events:
{events_json}

Return ONLY the JSON array of matching event IDs, ranked by relevance.""")
])

# Pydantic model for request body
class EventPreferencesRequest(BaseModel):
    date: str
    preferences: str  # Comma-separated preferences
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-11-15",
                "preferences": "music, entertainment, outdoor"
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

@app.get("/api/random-event")
def get_random_event():
    """
    Get a random event from Supabase with AI-generated conversational description.
    Fetches real events and presents them in a friendly, natural way.
    """
    try:
        # Fetch all events from Supabase
        response = supabase.table('events').select("*").execute()
        
        if not response.data or len(response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No events found in the database. Please add some events to Supabase."
                }
            )
        
        # Pick a random event
        event = random.choice(response.data)
        
        # Generate conversational description if LLM is available
        if llm_available and model:
            try:
                # Create the chain
                chain = event_prompt | model
                
                # Generate conversational description
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
                # Fallback if LLM fails
                print(f"LLM generation failed: {llm_error}")
                suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}! {event.get('description', 'An exciting event.')} It's on {event.get('date', 'soon')} at {event.get('time', 'TBA')}."
        else:
            # Fallback when LLM is not available
            suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}! {event.get('description', 'An exciting event.')} It's on {event.get('date', 'soon')} at {event.get('time', 'TBA')}."
        
        # Return the conversational response along with event data
        return JSONResponse(content={
            "success": True,
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
                "message": "Failed to fetch event from Supabase"
            }
        )

@app.get("/api/event/category/{category}")
def get_event_by_category(category: str):
    """
    Get a random event from a specific category with conversational AI description.
    Categories: concert, sports, outdoor, food, spiritual, cultural, kids, entertainment
    """
    try:
        # Fetch events by category from Supabase
        response = supabase.table('events').select("*").eq('category', category.lower()).execute()
        
        if not response.data or len(response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No {category} events found in the database."
                }
            )
        
        # Pick a random event from the category
        event = random.choice(response.data)
        
        # Create the chain
        chain = event_prompt | model
        
        # Generate conversational description
        llm_response = chain.invoke({
            "name": event.get("name", "Unknown Event"),
            "category": event.get("category", category),
            "description": event.get("description", "An exciting event"),
            "location": event.get("location", "Bangalore"),
            "date": event.get("date", "Soon"),
            "time": event.get("time", "TBA"),
            "price": event.get("price", "Contact organizer")
        })
        
        # Return the conversational response
        return JSONResponse(content={
            "success": True,
            "suggestion": llm_response.content,
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
            "source": "Supabase"
        })
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": f"Failed to fetch {category} events from Supabase"
            }
        )

@app.get("/api/events/all")
def get_all_events():
    """
    Get all events from Supabase (for testing and admin purposes)
    """
    try:
        response = supabase.table('events').select("*").execute()
        
        return JSONResponse(content={
            "success": True,
            "total_events": len(response.data),
            "events": response.data,
            "source": "Supabase"
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

@app.post("/api/events/by-preferences")
def get_event_by_date_prefs(request: EventPreferencesRequest):
    """
    Get events filtered by date and user preferences using MCP protocol.
    
    This endpoint:
    1. Fetches events from Supabase for the specified date
    2. Uses LLM with MCP-style filtering to match events with user preferences
    3. Returns ranked results with conversational AI descriptions
    
    Request body:
    - date: Event date (format: YYYY-MM-DD)
    - preferences: Comma-separated user preferences (e.g., "music, outdoor, family-friendly")
    """
    try:
        # Step 1: Fetch events from Supabase for the specified date
        response = supabase.table('events').select("*").eq('date', request.date).execute()
        
        if not response.data or len(response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No events found for date: {request.date}",
                    "date": request.date,
                    "preferences": request.preferences
                }
            )
        
        events = response.data
        
        # Step 2: Use MCP protocol to filter events based on preferences
        # Create a simplified version of events for LLM analysis
        events_for_llm = [
            {
                "id": str(event.get("id")),
                "name": event.get("name"),
                "category": event.get("category"),
                "description": event.get("description"),
                "price": event.get("price")
            }
            for event in events
        ]
        
        # Create MCP filtering chain
        mcp_chain = mcp_filter_prompt | model
        
        # Invoke LLM to filter and rank events
        mcp_response = mcp_chain.invoke({
            "preferences": request.preferences,
            "events_json": json.dumps(events_for_llm, indent=2)
        })
        
        # Parse the LLM response to get matching event IDs
        try:
            # Extract JSON array from response
            filtered_ids = json.loads(mcp_response.content.strip())
            
            if not isinstance(filtered_ids, list):
                # If LLM didn't return a proper array, fall back to all events
                filtered_ids = [str(e.get("id")) for e in events]
                
        except json.JSONDecodeError:
            # If parsing fails, return all events
            filtered_ids = [str(e.get("id")) for e in events]
        
        # Step 3: Get the filtered events in order
        filtered_events = []
        for event_id in filtered_ids:
            for event in events:
                if str(event.get("id")) == str(event_id):
                    filtered_events.append(event)
                    break
        
        # If no events matched after filtering, return all events
        if not filtered_events:
            filtered_events = events
        
        # Step 4: Generate conversational descriptions for top 3 results
        results_with_ai = []
        event_chain = event_prompt | model
        
        for i, event in enumerate(filtered_events[:3]):  # Only generate AI for top 3
            try:
                # Generate conversational description
                ai_response = event_chain.invoke({
                    "name": event.get("name", "Unknown Event"),
                    "category": event.get("category", "event"),
                    "description": event.get("description", "An exciting event"),
                    "location": event.get("location", "Bangalore"),
                    "date": event.get("date", request.date),
                    "time": event.get("time", "TBA"),
                    "price": event.get("price", "Contact organizer")
                })
                
                results_with_ai.append({
                    "rank": i + 1,
                    "suggestion": ai_response.content,
                    "event_details": {
                        "id": event.get("id"),
                        "name": event.get("name"),
                        "category": event.get("category"),
                        "description": event.get("description"),
                        "location": event.get("location"),
                        "date": event.get("date"),
                        "time": event.get("time"),
                        "price": event.get("price"),
                        "image_url": event.get("image_url"),
                        "booking_link": event.get("booking_link")
                    }
                })
            except Exception as e:
                # If AI generation fails, still include the event
                results_with_ai.append({
                    "rank": i + 1,
                    "suggestion": f"Found a {event.get('category', 'event')} event: {event.get('name', 'Unknown')} at {event.get('location', 'Bangalore')}",
                    "event_details": {
                        "id": event.get("id"),
                        "name": event.get("name"),
                        "category": event.get("category"),
                        "description": event.get("description"),
                        "location": event.get("location"),
                        "date": event.get("date"),
                        "time": event.get("time"),
                        "price": event.get("price"),
                        "image_url": event.get("image_url"),
                        "booking_link": event.get("booking_link")
                    }
                })
        
        # Return the results
        return JSONResponse(content={
            "success": True,
            "date": request.date,
            "preferences": request.preferences,
            "total_events_on_date": len(events),
            "matched_events": len(filtered_events),
            "top_results": results_with_ai,
            "all_matched_ids": [str(e.get("id")) for e in filtered_events],
            "source": "Supabase + MCP Filtering"
        })
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to fetch and filter events",
                "date": request.date,
                "preferences": request.preferences
            }
        )