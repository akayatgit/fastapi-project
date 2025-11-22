# Fix SSL certificate verification BEFORE any imports
import os
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Now import everything else
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from supabase import create_client, Client
from pydantic import BaseModel
import random
import json
import html
from datetime import datetime
from typing import List, Dict, Any
import asyncio
import time
from app.core.config import settings

app = FastAPI(
    title="Spotive Travel Agent Concierge API",
    description="AI-Powered Travel Package Discovery API for Travel Agents",
    version="0.2.0 (Travel Agent Concierge)"
)

# Audit logging storage (in-memory for MVP, can be moved to database later)
audit_logs: List[Dict[str, Any]] = []
MAX_LOGS = 1000  # Keep last 1000 logs

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Background task to log API calls to Supabase
def log_to_supabase(log_data: Dict[str, Any]):
    """Log API call details to Supabase for analytics (runs in background)"""
    try:
        supabase.table('api_logs').insert({
            "timestamp": log_data.get("timestamp"),
            "endpoint": log_data.get("endpoint"),
            "interests": log_data.get("interests"),
            "mapped_categories": log_data.get("mapped_categories"),
            "mapping_method": log_data.get("mapping_method"),  # "llm" or "keyword_fallback"
            "total_matching_events": log_data.get("total_matching_events"),
            "selected_event_id": log_data.get("selected_event_id"),
            "selected_event_name": log_data.get("selected_event_name"),
            "selected_event_category": log_data.get("selected_event_category"),
            "success": log_data.get("success"),
            "error_message": log_data.get("error_message"),
            "response_time_ms": log_data.get("response_time_ms"),
            "client_ip": log_data.get("client_ip"),
            "user_agent": log_data.get("user_agent")
        }).execute()
    except Exception as e:
        print(f"Failed to log to Supabase: {e}")

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

# Create the prompt template for conversational package descriptions
package_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Spotive, a friendly AI travel concierge assistant helping clients discover travel packages. 
    
    You'll be given details about a travel package. Your job is to present it in an exciting, conversational way.
    
    IMPORTANT: Respond in exactly 25 words, talking naturally like you're chatting with a friend over the phone.
    - Line 1: Introduce the package in an exciting way
    - Line 2: Share what makes it special or what they'll experience
    - Line 3: Mention destination, duration, and price in a casual way
    
    Be enthusiastic but natural! Help them visualize the amazing experience.
    Don't use JSON or structured data - just talk like a normal person would."""),
    ("human", """Tell me about this travel package in a friendly, conversational way:
    
Package Name: {name}
Category: {category}
Description: {description}
Destination: {destination}
Duration: {duration_days} days
Price: {price_range}""")
])

# LLM prompt to map interests to package categories
category_mapping_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent category mapping system for Spotive travel package discovery.

Your job is to map user interests to our predefined travel package categories.

**Predefined Categories (ONLY use these exactly):**
- adventure (adventure tours, trekking, extreme sports, hiking, mountaineering, bungee jumping, rafting)
- family (family-friendly packages, kid-friendly vacations, multi-generational travel)
- honeymoon (romantic honeymoon packages, couples retreats, romantic getaways)
- luxury (high-end luxury packages, premium experiences, VIP travel)
- beach (beach vacations, seaside resorts, coastal destinations)
- cultural (cultural tours, heritage sites, historical places, traditional experiences)
- spiritual (religious tours, pilgrimage, meditation retreats, spiritual journeys)
- sports (sports-related packages, golf tours, cricket tours, sports events)
- cruise (cruise packages, ocean cruises, river cruises)
- safari (wildlife safari packages, jungle tours, animal watching)
- wellness (spa retreats, yoga packages, wellness vacations, health retreats)
- group (group tour packages, friends trips, organized tours)
- solo (solo traveler packages, solo-friendly destinations)
- corporate (corporate retreats, business travel, MICE packages)

**CRITICAL RULES:**
1. Return ONLY categories that ACTUALLY match the user's interests
2. Do NOT return all categories - be selective!
3. Maximum 3 categories per response
4. If only one category matches, return only that one
5. Return ONLY a JSON array of category names
6. Use EXACT category names from the list above

**Examples (Follow these patterns - BE SELECTIVE!):**
- "honeymoon" → ["honeymoon"]
- "romantic getaway" → ["honeymoon"]
- "beach vacation" → ["beach"]
- "trekking adventure" → ["adventure"]
- "family trip" → ["family"]
- "luxury holiday" → ["luxury"]
- "yoga retreat" → ["wellness"]
- "wildlife safari" → ["safari"]
- "cultural heritage" → ["cultural"]
- "beach, luxury" → ["beach", "luxury"]
- "family, beach" → ["family", "beach"]
- "honeymoon, beach" → ["honeymoon", "beach"]
- "adventure, trekking" → ["adventure"]

**DO NOT return all 14 categories - only return what matches!**
"""),
    ("human", "User interests: {interests}\n\nReturn ONLY the JSON array of matching categories (max 3):")
])

# Pydantic models for requests and responses
class PackageInterestsRequest(BaseModel):
    interests: str  # Comma-separated interests
    phone_number: str = None  # Optional: for personalized recommendations
    travel_agent_id: str = None  # Optional: filter packages by travel agent
    user_name: str  # Required: user name to store in user profile and search history
    user_source: str  # Required: source information (e.g., city) to store in user profile and search history
    is_domestic: bool = None  # Optional: indicates if the search is for domestic packages
    
    class Config:
        json_schema_extra = {
            "example": {
                "interests": "honeymoon, beach, romantic",
                "phone_number": "+919876543210",
                "travel_agent_id": "spotive-travel",
                "user_name": "John Doe",
                "user_source": "Mumbai",
                "is_domestic": True
            }
        }

class PackageDestinationRequest(BaseModel):
    destination: str  # Destination name (e.g., "Maldives", "Bali")
    phone_number: str = None  # Optional: for personalized recommendations
    travel_agent_id: str = None  # Optional: filter packages by travel agent
    
    class Config:
        json_schema_extra = {
            "example": {
                "destination": "Maldives",
                "phone_number": "+919876543210",
                "travel_agent_id": "spotive-travel"
            }
        }

class UserRegisterRequest(BaseModel):
    phone_number: str
    username: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+919876543210",
                "username": "Ashok Kumar"
            }
        }

class UserPreferencesUpdate(BaseModel):
    preferred_categories: List[str] = None
    preferred_destinations: List[str] = None  # Changed from preferred_locations
    preferred_duration_days: Dict[str, int] = None  # {"min": 5, "max": 10}
    price_range: Dict[str, Any] = None  # {"min": 50000, "max": 200000, "currency": "INR"}
    avoid_categories: List[str] = None
    avoid_destinations: List[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferred_categories": ["honeymoon", "beach"],
                "preferred_destinations": ["Maldives", "Bali"],
                "preferred_duration_days": {"min": 5, "max": 10},
                "price_range": {"min": 100000, "max": 300000, "currency": "INR"},
                "avoid_categories": ["safari"],
                "avoid_destinations": []
            }
        }

class DiscoverPackagesRequest(BaseModel):
    interests: str = None  # Optional: can use profile only if empty
    
    class Config:
        json_schema_extra = {
            "example": {
                "interests": "honeymoon"
            }
        }

# Hotel management models removed - not needed for Travel Agent Concierge

# Helper functions for user management
import re

def validate_phone_number(phone: str) -> bool:
    """Validate international phone number format: +[country_code][number]"""
    # Basic international format: + followed by 7-15 digits
    pattern = r'^\+[1-9][0-9]{6,14}$'
    return bool(re.match(pattern, phone))

def get_or_create_user(phone_number: str, username: str = None) -> Dict[str, Any]:
    """Get existing user or create new one"""
    try:
        # Check if user exists
        response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        
        if response.data and len(response.data) > 0:
            # Update last_active
            user = response.data[0]
            supabase.table('users').update({
                "last_active": datetime.now().isoformat()
            }).eq('phone_number', phone_number).execute()
            return user
        else:
            # Create new user
            new_user = {
                "phone_number": phone_number,
                "username": username or "User",
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "total_searches": 0,
                "favorite_categories": {}
            }
            response = supabase.table('users').insert(new_user).execute()
            return response.data[0] if response.data else new_user
    except Exception as e:
        print(f"Error in get_or_create_user: {e}")
        return None

def track_user_search(phone_number: str, search_query: str, search_type: str, mapped_categories: list = None, destination: str = None, results_count: int = 0, user_name: str = None, user_source: str = None, is_domestic: bool = None):
    """Track user search and accumulate preferences (supports both interests and destination searches)"""
    try:
        # Get user
        user_response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        if not user_response.data:
            return
        
        user = user_response.data[0]
        user_id = user.get('id')
        
        # Insert search history
        search_entry = {
            "user_id": user_id,
            "search_query": search_query,
            "search_type": search_type,  # 'interests' or 'destination'
            "mapped_categories": mapped_categories or [],
            "search_timestamp": datetime.now().isoformat(),
            "results_count": results_count
        }
        
        # Add destination (optional field)
        if destination:
            search_entry["destination"] = destination
        
        # Add user_name and user_source (required fields)
        if user_name:
            search_entry["user_name"] = user_name
        if user_source:
            search_entry["user_source"] = user_source
        # Add is_domestic (optional field)
        if is_domestic is not None:
            search_entry["is_domestic"] = is_domestic
        
        supabase.table('user_search_history').insert(search_entry).execute()
        
        # Update user's favorite_categories (accumulate preferences)
        favorite_categories = user.get('favorite_categories', {})
        if not isinstance(favorite_categories, dict):
            favorite_categories = {}
        
        if mapped_categories:
            for category in mapped_categories:
                favorite_categories[category] = favorite_categories.get(category, 0) + 1
        
        # Update user's favorite_destinations (if destination search)
        favorite_destinations = user.get('favorite_destinations', {})
        if not isinstance(favorite_destinations, dict):
            favorite_destinations = {}
        
        if destination:
            favorite_destinations[destination] = favorite_destinations.get(destination, 0) + 1
        
        # Update user record
        update_data = {
            "total_searches": user.get('total_searches', 0) + 1,
            "last_active": datetime.now().isoformat()
        }
        
        if mapped_categories:
            update_data["favorite_categories"] = favorite_categories
        if destination:
            update_data["favorite_destinations"] = favorite_destinations
        
        # Update user_name and user_source (required fields)
        if user_name:
            update_data["username"] = user_name
        if user_source:
            update_data["user_source"] = user_source
        # Update is_domestic (optional field)
        if is_domestic is not None:
            update_data["is_domestic"] = is_domestic
        
        supabase.table('users').update(update_data).eq('phone_number', phone_number).execute()
        
    except Exception as e:
        print(f"Error tracking user search: {e}")

def get_user_top_categories(phone_number: str, limit: int = 3) -> List[str]:
    """Get user's top categories based on accumulated preferences"""
    try:
        user_response = supabase.table('users').select("favorite_categories").eq('phone_number', phone_number).execute()
        if not user_response.data:
            return []
        
        favorite_categories = user_response.data[0].get('favorite_categories', {})
        if not isinstance(favorite_categories, dict):
            return []
        
        # Sort by count and return top N
        sorted_categories = sorted(favorite_categories.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories[:limit]]
    except Exception as e:
        print(f"Error getting user top categories: {e}")
        return []

# Keyword-based category matching as fallback (for packages)
def keyword_match_categories(interests: str, valid_categories: list) -> list:
    """
    Fallback keyword matching when LLM fails
    Maps interests to package categories using keyword matching
    """
    interests_lower = interests.lower()
    matched = []
    
    # Keyword mappings - must align with package categories
    keyword_map = {
        "adventure": ["adventure", "trek", "trekking", "hike", "hiking", "mountaineering", "bungee", "rafting", "extreme", "outdoor"],
        "family": ["family", "kid", "kids", "children", "child-friendly", "multi-generational"],
        "honeymoon": ["honeymoon", "romantic", "couples", "romance", "wedding", "anniversary"],
        "luxury": ["luxury", "luxurious", "premium", "vip", "exclusive", "high-end", "deluxe"],
        "beach": ["beach", "beaches", "seaside", "coastal", "island", "ocean", "sea", "tropical"],
        "cultural": ["cultural", "culture", "heritage", "historical", "history", "tradition", "traditional"],
        "spiritual": ["spiritual", "spirituality", "pilgrimage", "meditation", "religious", "temple", "church"],
        "sports": ["sports", "sport", "golf", "cricket", "football", "tennis", "athletic"],
        "cruise": ["cruise", "cruises", "ship", "ocean cruise", "river cruise"],
        "safari": ["safari", "wildlife", "jungle", "animal", "zoo", "national park", "conservation"],
        "wellness": ["wellness", "spa", "yoga", "retreat", "health", "meditation", "relaxation"],
        "group": ["group", "groups", "friends", "organized", "tour group"],
        "solo": ["solo", "alone", "solo travel", "solo-friendly", "independent"],
        "corporate": ["corporate", "business", "mice", "conference", "retreat", "team building"],
    }
    
    # Check each category
    for category, keywords in keyword_map.items():
        if category in valid_categories:
            for keyword in keywords:
                if keyword in interests_lower:
                    if category not in matched:
                        matched.append(category)
                    break
    
    # If no matches found, return empty (will trigger error message)
    return matched[:3]  # Max 3 categories

# Middleware to log all API calls
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses for audit and debugging"""
    start_time = datetime.now()
    
    # Capture request details
    log_entry = {
        "timestamp": start_time.isoformat(),
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_headers": dict(request.headers)
    }
    
    # Capture request body for POST requests
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                try:
                    log_entry["request_body"] = json.loads(body.decode())
                except:
                    log_entry["request_body"] = body.decode() if body else None
            else:
                log_entry["request_body"] = None
            # Recreate request with body for downstream processing
            async def receive():
                return {"type": "http.request", "body": body}
            request = Request(request.scope, receive=receive)
        except Exception as e:
            log_entry["request_body_error"] = str(e)
            log_entry["request_body"] = body.decode() if body else None
    
    # Process request
    try:
        response = await call_next(request)
        log_entry["status_code"] = response.status_code
        log_entry["success"] = 200 <= response.status_code < 400
        log_entry["error"] = None
        
        # Capture response headers
        log_entry["response_headers"] = dict(response.headers)
        
        # Capture response body by reading it
        try:
            if hasattr(response, 'body_iterator'):
                # For streaming responses, we can't easily capture body
                log_entry["response_body"] = None
            elif isinstance(response, JSONResponse):
                # For JSONResponse, we can get the content
                if hasattr(response, 'body'):
                    body_bytes = response.body
                    if body_bytes:
                        try:
                            log_entry["response_body"] = json.loads(body_bytes.decode())
                        except:
                            log_entry["response_body"] = body_bytes.decode()[:2000]  # Limit to 2000 chars
                elif hasattr(response, 'content'):
                    # Try to get content directly
                    try:
                        if isinstance(response.content, (dict, list)):
                            log_entry["response_body"] = response.content
                        elif isinstance(response.content, str):
                            try:
                                log_entry["response_body"] = json.loads(response.content)
                            except:
                                log_entry["response_body"] = response.content[:2000]
                        else:
                            log_entry["response_body"] = None
                    except:
                        log_entry["response_body"] = None
                else:
                    log_entry["response_body"] = None
            elif isinstance(response, HTMLResponse):
                # For HTML responses, capture a snippet
                if hasattr(response, 'content') and response.content:
                    content_str = response.content if isinstance(response.content, str) else response.content.decode()[:500]
                    log_entry["response_body"] = f"<HTML Response (truncated): {len(content_str)} chars>"
                else:
                    log_entry["response_body"] = None
            else:
                log_entry["response_body"] = None
        except Exception as e:
            log_entry["response_body"] = None
            log_entry["response_body_error"] = str(e)
            
    except Exception as e:
        log_entry["status_code"] = 500
        log_entry["success"] = False
        log_entry["error"] = str(e)
        log_entry["error_type"] = type(e).__name__
        log_entry["response_headers"] = {}
        log_entry["response_body"] = None
        # Create error response
        response = JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
    finally:
        # Calculate duration
        end_time = datetime.now()
        log_entry["duration_ms"] = round((end_time - start_time).total_seconds() * 1000, 2)
        
        # Add to audit logs (keep only last MAX_LOGS entries)
        audit_logs.append(log_entry)
        if len(audit_logs) > MAX_LOGS:
            audit_logs.pop(0)
    
    return response

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

# ==================== HOTEL MANAGEMENT ENDPOINTS ====================

# ==================== USER MANAGEMENT ENDPOINTS ====================
# Note: All hotel-related endpoints have been removed for Travel Agent Concierge use case

@app.post("/api/users/register")
def register_user(request: UserRegisterRequest):
    """
    Register a new user or get existing user
    
    Request body:
    - phone_number: Indian phone number in format +91XXXXXXXXXX
    - username: User's name
    
    Returns user profile with accumulated preferences
    """
    try:
        # Validate phone number
        if not validate_phone_number(request.phone_number):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid phone number format. Use: +91XXXXXXXXXX (10 digits after +91)"
                }
            )
        
        # Get or create user
        user = get_or_create_user(request.phone_number, request.username)
        
        if not user:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to register user"
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "message": "User registered successfully" if user.get('total_searches', 0) == 0 else "Welcome back!",
            "user": {
                "id": user.get("id"),
                "phone_number": user.get("phone_number"),
                "username": user.get("username"),
                "created_at": user.get("created_at"),
                "last_active": user.get("last_active"),
                "total_searches": user.get("total_searches", 0),
                "favorite_categories": user.get("favorite_categories", {}),
                "top_3_interests": get_user_top_categories(request.phone_number, 3)
            }
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/users/{phone_number}")
def get_user_profile(phone_number: str):
    """
    Get user profile and accumulated preferences
    
    Path parameter:
    - phone_number: Indian phone number in format +91XXXXXXXXXX
    
    Returns complete user profile with search history and preferences
    """
    try:
        # Validate phone number
        if not validate_phone_number(phone_number):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid phone number format. Use: +91XXXXXXXXXX"
                }
            )
        
        # Get user
        user_response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        
        if not user_response.data or len(user_response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "User not found. Please register first at /api/users/register"
                }
            )
        
        user = user_response.data[0]
        
        # Get user's search history (last 10)
        search_history_response = supabase.table('user_search_history')\
            .select("*")\
            .eq('user_id', user.get('id'))\
            .order('search_timestamp', desc=True)\
            .limit(10)\
            .execute()
        
        # Get user preferences if exists
        preferences_response = supabase.table('user_preferences')\
            .select("*")\
            .eq('user_id', user.get('id'))\
            .execute()
        
        preferences = preferences_response.data[0] if preferences_response.data else None
        
        return JSONResponse(content={
            "success": True,
            "user": {
                "id": user.get("id"),
                "phone_number": user.get("phone_number"),
                "username": user.get("username"),
                "created_at": user.get("created_at"),
                "last_active": user.get("last_active"),
                "total_searches": user.get("total_searches", 0),
                "favorite_categories": user.get("favorite_categories", {}),
                "top_3_interests": get_user_top_categories(phone_number, 3)
            },
            "preferences": preferences if preferences else {
                "preferred_categories": [],
                "preferred_locations": [],
                "preferred_time_slots": [],
                "price_range": None,
                "avoid_categories": []
            },
            "recent_searches": [
                {
                    "query": search.get("search_query"),
                    "categories": search.get("mapped_categories"),
                    "timestamp": search.get("search_timestamp"),
                    "results_count": search.get("results_count")
                }
                for search in search_history_response.data
            ] if search_history_response.data else []
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.put("/api/users/{phone_number}/preferences")
def update_user_preferences(phone_number: str, preferences: UserPreferencesUpdate):
    """
    Update user preferences manually
    
    Path parameter:
    - phone_number: Indian phone number
    
    Request body:
    - preferred_categories: List of preferred event categories
    - preferred_locations: List of preferred locations in Bangalore
    - preferred_time_slots: List of preferred time slots (morning, afternoon, evening, weekend)
    - price_range: Dict with min and max price
    - avoid_categories: List of categories to avoid
    
    All fields are optional - only provided fields will be updated
    """
    try:
        # Validate phone number
        if not validate_phone_number(phone_number):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid phone number format"
                }
            )
        
        # Check if user exists
        user_response = supabase.table('users').select("id").eq('phone_number', phone_number).execute()
        if not user_response.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "User not found. Please register first."
                }
            )
        
        user_id = user_response.data[0].get('id')
        
        # Check if preferences exist
        existing_prefs = supabase.table('user_preferences')\
            .select("*")\
            .eq('user_id', user_id)\
            .execute()
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        if preferences.preferred_categories is not None:
            update_data['preferred_categories'] = preferences.preferred_categories
        if preferences.preferred_locations is not None:
            update_data['preferred_locations'] = preferences.preferred_locations
        if preferences.preferred_time_slots is not None:
            update_data['preferred_time_slots'] = preferences.preferred_time_slots
        if preferences.price_range is not None:
            update_data['price_range'] = preferences.price_range
        if preferences.avoid_categories is not None:
            update_data['avoid_categories'] = preferences.avoid_categories
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        if existing_prefs.data:
            # Update existing preferences
            result = supabase.table('user_preferences')\
                .update(update_data)\
                .eq('user_id', user_id)\
                .execute()
        else:
            # Create new preferences
            update_data['user_id'] = user_id
            result = supabase.table('user_preferences')\
                .insert(update_data)\
                .execute()
        
        return JSONResponse(content={
            "success": True,
            "message": "Preferences updated successfully",
            "preferences": result.data[0] if result.data else update_data
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/users/{phone_number}/discover-packages")
def discover_packages_personalized(phone_number: str, request: DiscoverPackagesRequest, background_tasks: BackgroundTasks, req: Request):
    """
    Discover packages with personalization based on client profile
    
    Path parameter:
    - phone_number: Client's phone number
    
    Request body:
    - interests: Optional comma-separated interests. If empty, uses client's profile
    
    This endpoint combines client's search with their accumulated preferences for better recommendations
    """
    try:
        # Validate phone number
        if not validate_phone_number(phone_number):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid phone number format"
                }
            )
        
        # Get or create user
        user = get_or_create_user(phone_number)
        if not user:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to get user"}
            )
        
        # Get user's top categories
        user_top_categories = get_user_top_categories(phone_number, 3)
        
        # Determine interests to use
        if request.interests and request.interests.strip():
            # User provided interests - combine with profile
            combined_interests = request.interests
            if user_top_categories:
                combined_interests += ", " + ", ".join(user_top_categories)
        else:
            # No interests provided - use profile only
            if not user_top_categories:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "No interests provided and user has no search history. Please provide interests or make some searches first."
                    }
                )
            combined_interests = ", ".join(user_top_categories)
        
        # Use the same logic as /api/package/by-interests
        valid_categories = ["adventure", "family", "honeymoon", "luxury", "beach", "cultural", "spiritual", "sports", "cruise", "safari", "wellness", "group", "solo", "corporate"]
        
        # Map interests to categories
        categories = []
        mapping_method = "llm"
        
        if llm_available and model:
            try:
                mapping_chain = category_mapping_prompt | model
                mapping_response = mapping_chain.invoke({"interests": combined_interests})
                
                llm_raw_response = mapping_response.content.strip()
                categories = json.loads(llm_raw_response)
                
                if not isinstance(categories, list):
                    categories = []
                else:
                    categories = [cat.lower() for cat in categories if cat.lower() in valid_categories]
            except:
                categories = []
        
        if len(categories) == 0 or len(categories) > 4:
            categories = keyword_match_categories(combined_interests, valid_categories)
            mapping_method = "keyword_fallback"
        
        if not categories:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Could not map interests to package categories",
                    "hint": "Try: honeymoon, adventure, family, beach, luxury"
                }
            )
        
        # Query packages
        packages = []
        for category in categories:
            response = supabase.table('packages').select("*").eq('category', category).eq('is_active', True).order('is_featured', desc=True).execute()
            if response.data:
                packages.extend(response.data)
        
        if not packages:
            # Track search
            track_user_search(phone_number, combined_interests, "interests", categories, None, 0)
            
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No packages found matching your interests"
                }
            )
        
        # Select up to 5 packages
        selected_packages = packages[:5] if len(packages) > 5 else packages
        
        # Generate conversational descriptions
        packages_with_suggestions = []
        
        for package in selected_packages:
            if llm_available and model:
                try:
                    chain = package_prompt | model
                    llm_response = chain.invoke({
                        "name": package.get("name", "Unknown Package"),
                        "category": package.get("category", "package"),
                        "description": package.get("description") or package.get("short_description", "An amazing travel package"),
                        "destination": package.get("destination", "Unknown"),
                        "duration_days": package.get("duration_days", 0),
                        "price_range": package.get("price_range", "Contact for pricing")
                    })
                    suggestion = llm_response.content
                except:
                    suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}!"
            else:
                suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}!"
            
            packages_with_suggestions.append({
                "suggestion": suggestion,
                "package_details": {
                    "id": package.get("id"),
                    "name": package.get("name"),
                    "category": package.get("category"),
                    "destination": package.get("destination"),
                    "destination_country": package.get("destination_country"),
                    "duration_days": package.get("duration_days"),
                    "duration_nights": package.get("duration_nights"),
                    "price_range": package.get("price_range"),
                    "price_min": package.get("price_min"),
                    "price_max": package.get("price_max"),
                    "currency": package.get("currency"),
                    "inclusions": package.get("inclusions", []),
                    "exclusions": package.get("exclusions", []),
                    "highlights": package.get("highlights", []),
                    "image_urls": package.get("image_urls", []),
                    "main_image_url": package.get("main_image_url"),
                    "booking_link": package.get("booking_link"),
                    "travel_agent_id": package.get("travel_agent_id"),
                    "travel_agent_name": package.get("travel_agent_name")
                }
            })
        
        # Track search (accumulate preferences)
        track_user_search(phone_number, combined_interests, "interests", categories, None, len(packages))
        
        return JSONResponse(content={
            "success": True,
            "personalized": True,
            "user_top_categories": user_top_categories,
            "original_interests": request.interests,
            "combined_interests_used": combined_interests,
            "mapped_categories": categories,
            "mapping_method": mapping_method,
            "total_matching_packages": len(packages),
            "returned_packages": len(packages_with_suggestions),
            "packages": packages_with_suggestions,
            "source": "Supabase",
            "ai_generated": llm_available
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/package/by-interests")
def get_package_by_interests(
    request: PackageInterestsRequest, 
    background_tasks: BackgroundTasks, 
    req: Request
):
    """
    Get travel packages based on client interests.
    
    NOTE: This endpoint is called "GetPackagesAPI" in ElevenLabs webhook configuration.
    
    Request body:
    - interests: Comma-separated interests (e.g., "honeymoon, beach, romantic")
    - phone_number: Phone number for real-time results and tracking (+91XXXXXXXXXX or international)
    - travel_agent_id: Optional travel agent ID to filter packages
    - user_name: Required - user name to store in user profile and search history
    - user_source: Required - source information (e.g., city) to store in user profile and search history
    - is_domestic: Optional - indicates if the search is for domestic packages (True/False)
    
    The system will:
    1. Use AI to map interests to package categories
    2. Query packages matching those categories
    3. If travel_agent_id provided, filter packages by travel agent
    4. Return up to 5 matching packages with conversational descriptions
    5. If phone_number provided:
       - Track search history and accumulate preferences
       - Store user_name, user_source, and is_domestic in user profile and search history
       - Write results to search_results table for real-time push to frontend
       - Frontend subscribes to phone_number to receive results instantly
    
    NOTE: For full personalization features, use /api/users/{phone_number}/discover-packages
    """
    start_time = datetime.now()
    try:
        # Predefined package categories (must match database exactly)
        valid_categories = ["adventure", "family", "honeymoon", "luxury", "beach", "cultural", "spiritual", "sports", "cruise", "safari", "wellness", "group", "solo", "corporate"]
        
        # Step 1: Use LLM to map interests to categories
        categories = []
        
        if llm_available and model:
            try:
                mapping_chain = category_mapping_prompt | model
                mapping_response = mapping_chain.invoke({"interests": request.interests})
                
                # Parse the LLM response to get categories
                try:
                    llm_raw_response = mapping_response.content.strip()
                    print(f"DEBUG - LLM raw response for '{request.interests}': {llm_raw_response}")
                    
                    categories = json.loads(llm_raw_response)
                    print(f"DEBUG - Parsed categories: {categories}")
                    
                    if not isinstance(categories, list):
                        print(f"DEBUG - LLM returned non-list, using fallback")
                        categories = []
                    else:
                        # Filter to only valid categories
                        original_count = len(categories)
                        categories = [cat.lower() for cat in categories if cat.lower() in valid_categories]
                        print(f"DEBUG - After validation: {categories} (filtered from {original_count})")
                except json.JSONDecodeError as e:
                    print(f"DEBUG - JSON decode error: {e}, using fallback")
                    categories = []
            except Exception as e:
                print(f"Category mapping failed: {e}")
                categories = []
        
        # Validation: If LLM returned too many categories (>4) or none, use keyword fallback
        mapping_method = "llm"
        if len(categories) == 0 or len(categories) > 4:
            print(f"DEBUG - LLM returned invalid categories ({len(categories)}), using keyword matching fallback")
            categories = keyword_match_categories(request.interests, valid_categories)
            mapping_method = "keyword_fallback"
            print(f"DEBUG - Keyword matching result: {categories}")
        
        # Final validation: If still no categories, return error
        if not categories:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"Could not map interests '{request.interests}' to any package categories. Please try different interests.",
                    "valid_categories": valid_categories,
                    "hint": "Try: honeymoon, adventure, family, beach, luxury, cultural, wellness"
                }
            )
        
        # Step 2: Query Supabase for packages matching any of the categories
        packages = []
        package_ids = set()  # Track to avoid duplicates
        
        for category in categories:
            print(f"DEBUG - Searching for category: '{category}'")
            
            # Query by category - try multiple approaches
            response = None
            
            # Approach 1: Try with is_active=True
            try:
                query = supabase.table('packages').select("*").eq('category', category)
                
                # Filter by travel agent if provided
                if request.travel_agent_id:
                    query = query.eq('travel_agent_id', request.travel_agent_id)
                
                # Try with is_active=True first
                query_active = query.eq('is_active', True)
                response = query_active.order('is_featured', desc=True).order('display_order').execute()
                print(f"DEBUG - Query with is_active=True for '{category}': {len(response.data) if response.data else 0} packages")
                
                # If no results, try without is_active filter
                if not response.data or len(response.data) == 0:
                    print(f"DEBUG - No packages with is_active=True for '{category}', trying without filter...")
                    response = query.order('is_featured', desc=True).order('display_order').execute()
                    print(f"DEBUG - Query without is_active filter for '{category}': {len(response.data) if response.data else 0} packages")
                    
            except Exception as e:
                print(f"DEBUG - Query error for category '{category}': {e}")
                import traceback
                traceback.print_exc()
                # Try simple query as fallback
                try:
                    response = supabase.table('packages').select("*").eq('category', category).execute()
                except Exception as e2:
                    print(f"DEBUG - Fallback query also failed: {e2}")
                    response = None
            
            if response and response.data:
                print(f"DEBUG - Processing {len(response.data)} packages for category '{category}'")
                for pkg in response.data:
                    pkg_id = pkg.get('id')
                    pkg_name = pkg.get('name')
                    pkg_category = pkg.get('category')
                    pkg_is_active = pkg.get('is_active')
                    
                    print(f"DEBUG - Package details: id={pkg_id}, name={pkg_name}, category={pkg_category}, is_active={pkg_is_active}, type(is_active)={type(pkg_is_active)}")
                    
                    # Verify category matches (case-insensitive)
                    if pkg_category and pkg_category.lower() != category.lower():
                        print(f"DEBUG - Skipping {pkg_name}: category mismatch ('{pkg_category}' != '{category}')")
                        continue
                    
                    # Check if already added (by ID) - skip duplicates
                    if pkg_id in package_ids:
                        print(f"DEBUG - ⚠️ Skipped {pkg_name}: duplicate ID ({pkg_id})")
                        continue
                    
                    # Only include if is_active is not explicitly False
                    # Handle both boolean True and string "true" from database, or None
                    is_active_valid = True  # Default to include
                    if pkg_is_active is False:
                        is_active_valid = False
                    elif isinstance(pkg_is_active, str) and pkg_is_active.lower() in ('false', '0', 'no'):
                        is_active_valid = False
                    
                    if not is_active_valid:
                        print(f"DEBUG - ❌ Skipped {pkg_name}: is_active={pkg_is_active} (explicitly False)")
                        continue
                    
                    # Add the package - use ID or create temporary one
                    if pkg_id:
                        packages.append(pkg)
                        package_ids.add(pkg_id)
                        print(f"DEBUG - ✅ Added package: {pkg_name} (id: {pkg_id}, category: {pkg_category}, is_active: {pkg_is_active})")
                    else:
                        # Package without ID - still add it with a temporary identifier
                        temp_id = f"temp_{len(packages)}_{pkg_name}"
                        packages.append(pkg)
                        package_ids.add(temp_id)
                        print(f"DEBUG - ✅ Added package (no ID): {pkg_name} (category: {pkg_category}, is_active: {pkg_is_active})")
            else:
                print(f"DEBUG - ⚠️ No response data for category '{category}'")
                if response:
                    print(f"DEBUG - Response object: {response}")
                    print(f"DEBUG - Response.data: {response.data if hasattr(response, 'data') else 'No data attribute'}")
        
        # Summary after category search
        print(f"DEBUG - 📊 Summary after category search: {len(packages)} packages collected from {len(categories)} categories")
        if packages:
            print(f"DEBUG - 📦 Collected packages: {[p.get('name', 'Unknown') for p in packages[:5]]}")
        
        # Step 2.5: Also search by package name/description if no results (fuzzy search)
        if not packages:
            print(f"DEBUG - No packages found by category, trying name/description search...")
            search_terms = request.interests.lower().split()
            
            # Search each term in name, description, short_description
            for term in search_terms:
                # Search in name
                name_query = supabase.table('packages').select("*").ilike('name', f'%{term}%')
                if request.travel_agent_id:
                    name_query = name_query.eq('travel_agent_id', request.travel_agent_id)
                name_response = name_query.order('is_featured', desc=True).limit(5).execute()
                
                if name_response.data:
                    for pkg in name_response.data:
                        pkg_id = pkg.get('id')
                        if pkg_id and pkg_id not in package_ids and pkg.get('is_active') is not False:
                            packages.append(pkg)
                            package_ids.add(pkg_id)
                
                # Search in description
                desc_query = supabase.table('packages').select("*").ilike('description', f'%{term}%')
                if request.travel_agent_id:
                    desc_query = desc_query.eq('travel_agent_id', request.travel_agent_id)
                desc_response = desc_query.order('is_featured', desc=True).limit(5).execute()
                
                if desc_response.data:
                    for pkg in desc_response.data:
                        pkg_id = pkg.get('id')
                        if pkg_id and pkg_id not in package_ids and pkg.get('is_active') is not False:
                            packages.append(pkg)
                            package_ids.add(pkg_id)
            
            if packages:
                print(f"DEBUG - Found {len(packages)} packages by name/description search")
        
        # Critical check: Print packages list before final check
        print(f"DEBUG - 🔍 FINAL CHECK: packages list has {len(packages) if packages else 0} items")
        if packages:
            print(f"DEBUG - 🔍 Packages in list: {[p.get('name', 'Unknown') for p in packages[:5]]}")
        else:
            print(f"DEBUG - 🔍 Packages list is EMPTY!")
            print(f"DEBUG - 🔍 package_ids set: {package_ids}")
        
        if not packages or len(packages) == 0:
            # Debug: Check what packages exist in database
            debug_query = supabase.table('packages').select("id, name, category, is_active").limit(10).execute()
            total_packages = len(debug_query.data) if debug_query.data else 0
            print(f"DEBUG - Total packages in DB: {total_packages}")
            
            # Check packages by category
            category_packages = {}
            if debug_query.data:
                for pkg in debug_query.data:
                    cat = pkg.get('category')
                    if cat:
                        if cat not in category_packages:
                            category_packages[cat] = []
                        category_packages[cat].append({
                            "name": pkg.get('name'),
                            "is_active": pkg.get('is_active')
                        })
                print(f"DEBUG - Packages by category: {category_packages}")
            
            # Log to Supabase (async)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            background_tasks.add_task(log_to_supabase, {
                "timestamp": datetime.now().isoformat(),
                "endpoint": "/api/package/by-interests",
                "interests": request.interests,
                "mapped_categories": json.dumps(categories),
                "mapping_method": mapping_method,
                "total_matching_events": 0,
                "selected_event_id": None,
                "selected_event_name": None,
                "selected_event_category": None,
                "success": False,
                "error_message": f"No packages found matching interests: {request.interests}",
                "response_time_ms": response_time,
                "client_ip": req.client.host if req.client else "unknown",
                "user_agent": req.headers.get("user-agent", "unknown")
            })
            
            error_message = f"No packages found matching interests: {request.interests}"
            hint = "Check if packages exist in database with matching categories and is_active=true (or NULL)"
            
            if total_packages == 0:
                hint = "No packages found in database. Run CHECK_AND_FIX_PACKAGES.sql to insert sample data."
            elif category_packages:
                hint = f"Found packages in categories: {list(category_packages.keys())}. Searched for: {categories}. Check is_active status."
            
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": error_message,
                    "mapped_categories": categories,
                    "hint": hint,
                    "debug_info": {
                        "total_packages_in_db": total_packages,
                        "searched_categories": categories,
                        "available_categories": list(category_packages.keys()) if category_packages else []
                    }
                }
            )
        
        # Step 3: Select up to 5 packages (or all if less than 5)
        selected_packages = packages[:5] if len(packages) > 5 else packages
        
        # Step 4: Generate conversational descriptions for each package
        packages_with_suggestions = []
        
        for package in selected_packages:
            # Generate conversational description if LLM is available
            if llm_available and model:
                try:
                    chain = package_prompt | model
                    
                    llm_response = chain.invoke({
                        "name": package.get("name", "Unknown Package"),
                        "category": package.get("category", "package"),
                        "description": package.get("description") or package.get("short_description", "An amazing travel package"),
                        "destination": package.get("destination", "Unknown"),
                        "duration_days": package.get("duration_days", 0),
                        "price_range": package.get("price_range", "Contact for pricing")
                    })
                    suggestion = llm_response.content
                except Exception as llm_error:
                    print(f"LLM generation failed: {llm_error}")
                    suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}! {package.get('description', 'An amazing travel experience.')} Duration: {package.get('duration_days', 0)} days."
            else:
                suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}! {package.get('description', 'An amazing travel experience.')} Duration: {package.get('duration_days', 0)} days."
            
            package_details = {
                "id": package.get("id"),
                "name": package.get("name"),
                "category": package.get("category"),
                "destination": package.get("destination"),
                "destination_country": package.get("destination_country"),
                "duration_days": package.get("duration_days"),
                "duration_nights": package.get("duration_nights"),
                "price_range": package.get("price_range"),
                "price_min": package.get("price_min"),
                "price_max": package.get("price_max"),
                "currency": package.get("currency"),
                "inclusions": package.get("inclusions", []),
                "exclusions": package.get("exclusions", []),
                "highlights": package.get("highlights", []),
                "image_urls": package.get("image_urls", []),
                "main_image_url": package.get("main_image_url"),
                "booking_link": package.get("booking_link"),
                "travel_agent_id": package.get("travel_agent_id"),
                "travel_agent_name": package.get("travel_agent_name")
            }
            
            packages_with_suggestions.append({
                "suggestion": suggestion,
                "package_details": package_details
            })
        
        # Track user search if phone_number provided (optional)
        if request.phone_number:
            if validate_phone_number(request.phone_number):
                # Get or create user with name (required)
                user = get_or_create_user(request.phone_number, username=request.user_name)
                if user:
                    background_tasks.add_task(track_user_search, request.phone_number, request.interests, "interests", categories, None, len(packages), request.user_name, request.user_source, request.is_domestic)
        
        # Log to Supabase (async) - SUCCESS CASE
        first_package = selected_packages[0]
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/package/by-interests",
            "interests": request.interests,
            "mapped_categories": json.dumps(categories),
            "mapping_method": mapping_method,
            "total_matching_events": len(packages),
            "selected_event_id": first_package.get("id"),
            "selected_event_name": first_package.get("name"),
            "selected_event_category": first_package.get("category"),
            "success": True,
            "error_message": None,
            "response_time_ms": response_time,
            "client_ip": req.client.host if req.client else "unknown",
            "user_agent": req.headers.get("user-agent", "unknown")
        })
        
        # Return the conversational response
        response_data = {
            "success": True,
            "interests": request.interests,
            "mapped_categories": categories,
            "mapping_method": mapping_method,
            "total_matching_packages": len(packages),
            "returned_packages": len(packages_with_suggestions),
            "packages": packages_with_suggestions,
            "source": "Supabase",
            "ai_generated": llm_available,
            "personalized": bool(request.phone_number)
        }
        
        # Write results to search_results table for real-time push (if phone_number provided)
        if request.phone_number:
            try:
                # Generate timestamp in milliseconds for uniqueness
                timestamp_millis = int(time.time() * 1000)
                
                supabase.table('search_results').insert({
                    "phone_number": request.phone_number,
                    "timestamp_millis": timestamp_millis,
                    "results": response_data,
                    "travel_agent_id": request.travel_agent_id,
                    "created_at": datetime.now().isoformat(),
                    "is_domestic": request.is_domestic if request.is_domestic is not None else False
                }).execute()
                print(f"✅ Results written for phone: {request.phone_number} at {timestamp_millis}")
            except Exception as e:
                print(f"⚠️ Failed to write kiosk results: {e}")
                # Don't fail the request if this fails
        
        return JSONResponse(content=response_data)
            
    except Exception as e:
        # Log to Supabase (async) - ERROR CASE
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/package/by-interests",
            "interests": request.interests if hasattr(request, 'interests') else "unknown",
            "mapped_categories": None,
            "mapping_method": "error",
            "total_matching_events": 0,
            "selected_event_id": None,
            "selected_event_name": None,
            "selected_event_category": None,
            "success": False,
            "error_message": str(e),
            "response_time_ms": response_time,
            "client_ip": req.client.host if req.client else "unknown",
            "user_agent": req.headers.get("user-agent", "unknown")
        })
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to fetch packages from Supabase"
            }
        )

@app.post("/api/package/by-destination")
def get_package_by_destination(
    request: PackageDestinationRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Get travel packages for a specific destination.
    
    Request body:
    - destination: Destination name (e.g., "Maldives", "Bali", "Switzerland")
    - phone_number: Phone number for real-time results and tracking (+91XXXXXXXXXX or international)
    - travel_agent_id: Optional travel agent ID to filter packages
    
    The system will:
    1. Query packages matching the destination name (case-insensitive)
    2. Filter by travel agent if provided
    3. Return up to 10 matching packages with conversational descriptions
    4. If phone_number provided:
       - Track search history and accumulate destination preferences
       - Write results to search_results table for real-time push to frontend
       - Frontend subscribes to phone_number to receive results instantly
    """
    start_time = datetime.now()
    try:
        destination = request.destination.strip()
        
        if not destination:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Destination is required"
                }
            )
        
        # Query packages by destination (case-insensitive)
        query = supabase.table('packages').select("*").ilike('destination', f"%{destination}%").eq('is_active', True)
        
        # Also search in destination_country
        query_or = supabase.table('packages').select("*").ilike('destination_country', f"%{destination}%").eq('is_active', True)
        
        # Filter by travel agent if provided
        if request.travel_agent_id:
            query = query.eq('travel_agent_id', request.travel_agent_id)
            query_or = query_or.eq('travel_agent_id', request.travel_agent_id)
        
        response = query.order('is_featured', desc=True).order('display_order').execute()
        response_or = query_or.order('is_featured', desc=True).order('display_order').execute()
        
        packages = []
        package_ids = set()
        
        # Combine results and remove duplicates
        for package in (response.data or []):
            if package.get('id') not in package_ids:
                packages.append(package)
                package_ids.add(package.get('id'))
        
        for package in (response_or.data or []):
            if package.get('id') not in package_ids:
                packages.append(package)
                package_ids.add(package.get('id'))
        
        if not packages:
            # Track search if phone number provided
            if request.phone_number and validate_phone_number(request.phone_number):
                background_tasks.add_task(track_user_search, request.phone_number, destination, "destination", None, destination, 0)
            
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No packages found for destination: {destination}"
                }
            )
        
        # Select up to 10 packages (destination searches can have more results)
        selected_packages = packages[:10] if len(packages) > 10 else packages
        
        # Generate conversational descriptions
        packages_with_suggestions = []
        
        for package in selected_packages:
            if llm_available and model:
                try:
                    chain = package_prompt | model
                    llm_response = chain.invoke({
                        "name": package.get("name", "Unknown Package"),
                        "category": package.get("category", "package"),
                        "description": package.get("description") or package.get("short_description", "An amazing travel package"),
                        "destination": package.get("destination", "Unknown"),
                        "duration_days": package.get("duration_days", 0),
                        "price_range": package.get("price_range", "Contact for pricing")
                    })
                    suggestion = llm_response.content
                except Exception as llm_error:
                    print(f"LLM generation failed: {llm_error}")
                    suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}! {package.get('description', 'An amazing travel experience.')} Duration: {package.get('duration_days', 0)} days."
            else:
                suggestion = f"Check out {package.get('name', 'this package')} in {package.get('destination', 'amazing destination')}! {package.get('description', 'An amazing travel experience.')} Duration: {package.get('duration_days', 0)} days."
            
            package_details = {
                "id": package.get("id"),
                "name": package.get("name"),
                "category": package.get("category"),
                "destination": package.get("destination"),
                "destination_country": package.get("destination_country"),
                "destination_city": package.get("destination_city"),
                "duration_days": package.get("duration_days"),
                "duration_nights": package.get("duration_nights"),
                "price_range": package.get("price_range"),
                "price_min": package.get("price_min"),
                "price_max": package.get("price_max"),
                "currency": package.get("currency"),
                "inclusions": package.get("inclusions", []),
                "exclusions": package.get("exclusions", []),
                "highlights": package.get("highlights", []),
                "image_urls": package.get("image_urls", []),
                "main_image_url": package.get("main_image_url"),
                "booking_link": package.get("booking_link"),
                "travel_agent_id": package.get("travel_agent_id"),
                "travel_agent_name": package.get("travel_agent_name")
            }
            
            packages_with_suggestions.append({
                "suggestion": suggestion,
                "package_details": package_details
            })
        
        # Track user search if phone_number provided
        if request.phone_number:
            if validate_phone_number(request.phone_number):
                user = get_or_create_user(request.phone_number)
                if user:
                    background_tasks.add_task(track_user_search, request.phone_number, destination, "destination", None, destination, len(packages))
        
        # Log to Supabase (async) - SUCCESS CASE
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        first_package = selected_packages[0] if selected_packages else None
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/package/by-destination",
            "interests": destination,
            "mapped_categories": json.dumps([]),
            "mapping_method": "destination_search",
            "total_matching_events": len(packages),
            "selected_event_id": first_package.get("id") if first_package else None,
            "selected_event_name": first_package.get("name") if first_package else None,
            "selected_event_category": first_package.get("category") if first_package else None,
            "success": True,
            "error_message": None,
            "response_time_ms": response_time,
            "client_ip": req.client.host if req.client else "unknown",
            "user_agent": req.headers.get("user-agent", "unknown")
        })
        
        # Return response
        response_data = {
            "success": True,
            "destination": destination,
            "total_matching_packages": len(packages),
            "returned_packages": len(packages_with_suggestions),
            "packages": packages_with_suggestions,
            "source": "Supabase",
            "ai_generated": llm_available,
            "personalized": bool(request.phone_number)
        }
        
        # Write results to search_results table for real-time push (if phone_number provided)
        if request.phone_number:
            try:
                timestamp_millis = int(time.time() * 1000)
                
                supabase.table('search_results').insert({
                    "phone_number": request.phone_number,
                    "timestamp_millis": timestamp_millis,
                    "results": response_data,
                    "travel_agent_id": request.travel_agent_id,
                    "created_at": datetime.now().isoformat(),
                    "is_domestic": False  # Default to False for destination searches (can be updated if needed)
                }).execute()
                print(f"✅ Results written for phone: {request.phone_number} at {timestamp_millis}")
            except Exception as e:
                print(f"⚠️ Failed to write kiosk results: {e}")
        
        return JSONResponse(content=response_data)
            
    except Exception as e:
        # Log to Supabase (async) - ERROR CASE
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/package/by-destination",
            "interests": request.destination if hasattr(request, 'destination') else "unknown",
            "mapped_categories": None,
            "mapping_method": "error",
            "total_matching_events": 0,
            "selected_event_id": None,
            "selected_event_name": None,
            "selected_event_category": None,
            "success": False,
            "error_message": str(e),
            "response_time_ms": response_time,
            "client_ip": req.client.host if req.client else "unknown",
            "user_agent": req.headers.get("user-agent", "unknown")
        })
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to fetch packages from Supabase"
            }
        )

@app.get("/api/logs", response_class=HTMLResponse)
def view_audit_logs(
    time_filter: str = "all",  # all, hour, day, week
    endpoint: str = "all",  # all or specific endpoint
    status: str = "all"  # all, success, failed
):
    """
    View all audit logs in a nice HTML format for debugging with filters
    """
    # Return simple HTML without complex CSS that causes f-string issues
    return HTMLResponse(content=generate_logs_html(time_filter, endpoint, status))

def generate_logs_html(time_filter: str = "all", endpoint: str = "all", status: str = "all"):
    """Generate HTML for logs page (separate function to avoid f-string CSS issues)"""
    from datetime import timedelta
    
    # Filter logs based on criteria
    filtered_logs = audit_logs.copy()
    
    # Time filtering
    now = datetime.now()
    if time_filter == "hour":
        cutoff = now - timedelta(hours=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "day":
        cutoff = now - timedelta(days=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "week":
        cutoff = now - timedelta(weeks=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    
    # Endpoint filtering
    if endpoint != "all":
        filtered_logs = [log for log in filtered_logs if log.get("path") == endpoint]
    
    # Status filtering
    if status == "success":
        filtered_logs = [log for log in filtered_logs if log.get("success", False)]
    elif status == "failed":
        filtered_logs = [log for log in filtered_logs if not log.get("success", True)]
    
    # Calculate statistics from filtered logs
    total_logs = len(filtered_logs)
    successful_logs = sum(1 for log in filtered_logs if log.get("success", False))
    failed_logs = total_logs - successful_logs
    success_rate = round((successful_logs / total_logs * 100) if total_logs > 0 else 0, 1)
    avg_duration = round(sum(log.get("duration_ms", 0) for log in filtered_logs) / total_logs if total_logs > 0 else 0, 2)
    
    # Get unique endpoints for filter dropdown
    unique_endpoints = sorted(set(log.get("path", "") for log in audit_logs if log.get("path")))
    
    # Generate log entries HTML
    log_entries_html = ""
    if total_logs > 0:
        for log in reversed(filtered_logs):  # Show newest first
            success_class = "success" if log.get("success", False) else "error"
            status_class = "success" if log.get("success", False) else "error"
            
            # Format request headers
            request_headers_html = ""
            if "request_headers" in log and log["request_headers"]:
                headers_str = json.dumps(dict(log["request_headers"]), indent=2)
                headers_str_escaped = html.escape(headers_str)
                request_headers_html = f"""
                <div class="collapsible-section">
                    <button class="collapsible-btn" onclick="toggleSection(this)">📋 Request Headers</button>
                    <div class="collapsible-content">
                        <div class="json-box">
                            <pre>{headers_str_escaped}</pre>
                        </div>
                    </div>
                </div>
                """
            
            # Format request body
            request_body_html = ""
            if "request_body" in log and log["request_body"]:
                body_str = json.dumps(log["request_body"], indent=2) if isinstance(log["request_body"], (dict, list)) else str(log["request_body"])
                body_str_escaped = html.escape(body_str)
                request_body_html = f"""
                <div class="collapsible-section">
                    <button class="collapsible-btn" onclick="toggleSection(this)">📤 Request Body</button>
                    <div class="collapsible-content">
                        <div class="json-box">
                            <pre>{body_str_escaped}</pre>
                        </div>
                    </div>
                </div>
                """
            
            # Format response headers
            response_headers_html = ""
            if "response_headers" in log and log["response_headers"]:
                resp_headers_str = json.dumps(dict(log["response_headers"]), indent=2)
                resp_headers_str_escaped = html.escape(resp_headers_str)
                response_headers_html = f"""
                <div class="collapsible-section">
                    <button class="collapsible-btn" onclick="toggleSection(this)">📥 Response Headers</button>
                    <div class="collapsible-content">
                        <div class="json-box">
                            <pre>{resp_headers_str_escaped}</pre>
                        </div>
                    </div>
                </div>
                """
            
            # Format response body
            response_body_html = ""
            if "response_body" in log and log["response_body"] is not None:
                if isinstance(log["response_body"], (dict, list)):
                    resp_body_str = json.dumps(log["response_body"], indent=2)
                else:
                    resp_body_str = str(log["response_body"])
                resp_body_str_escaped = html.escape(resp_body_str)
                response_body_html = f"""
                <div class="collapsible-section">
                    <button class="collapsible-btn" onclick="toggleSection(this)">📥 Response Body</button>
                    <div class="collapsible-content">
                        <div class="json-box">
                            <pre>{resp_body_str_escaped}</pre>
                        </div>
                    </div>
                </div>
                """
            
            # Format error
            error_html = ""
            if log.get("error"):
                error_html = f"""
                <div class="error-box">
                    <strong>❌ Error:</strong> {log["error"]}<br>
                    <strong>Type:</strong> {log.get("error_type", "Unknown")}
                </div>
                """
            
            log_entries_html += f"""
            <div class="log-entry {success_class}">
                <div class="log-header">
                    <div>
                        <span class="method {log['method']}">{log['method']}</span>
                        <strong>{log['path']}</strong>
                    </div>
                    <div>
                        <span class="status {status_class}">Status: {log.get('status_code', 'N/A')}</span>
                    </div>
                </div>
                <div class="log-details">
                    <div class="log-row">
                        <div class="log-label">Timestamp:</div>
                        <div class="log-value">{log['timestamp']}</div>
                    </div>
                    <div class="log-row">
                        <div class="log-label">Client IP:</div>
                        <div class="log-value">{log.get('client_ip', 'unknown')}</div>
                    </div>
                    <div class="log-row">
                        <div class="log-label">User Agent:</div>
                        <div class="log-value">{log.get('user_agent', 'unknown')}</div>
                    </div>
                    <div class="log-row">
                        <div class="log-label">Duration:</div>
                        <div class="log-value">{log.get('duration_ms', 0)} ms</div>
                    </div>
                    {request_headers_html}
                    {request_body_html}
                    {response_headers_html}
                    {response_body_html}
                    {error_html}
                </div>
            </div>
            """
    else:
        log_entries_html = "<p style='text-align: center; color: #999; font-size: 1.2em; padding: 40px;'>📭 No logs yet. Make some API calls to see them here!</p>"
    
    html_content = """<!DOCTYPE html>
    <html>
    <head>
        <title>Spotive API - Audit Logs</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .stats {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                flex: 1;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .log-entry {
                background: white;
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
            }
            .log-entry.error {
                border-left-color: #e74c3c;
            }
            .log-entry.success {
                border-left-color: #2ecc71;
            }
            .log-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.85em;
            }
            .method.POST { background: #3498db; color: white; }
            .method.GET { background: #2ecc71; color: white; }
            .method.PUT { background: #f39c12; color: white; }
            .method.DELETE { background: #e74c3c; color: white; }
            .status {
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }
            .status.success { background: #d4edda; color: #155724; }
            .status.error { background: #f8d7da; color: #721c24; }
            .log-details {
                margin-top: 10px;
                font-size: 0.9em;
            }
            .log-row {
                margin: 5px 0;
                display: flex;
            }
            .log-label {
                font-weight: bold;
                min-width: 150px;
                color: #666;
            }
            .log-value {
                flex: 1;
                font-family: 'Courier New', monospace;
                word-break: break-all;
            }
            .json-box {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                margin-top: 5px;
            }
            pre {
                margin: 0;
                white-space: pre-wrap;
            }
            .error-box {
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
            }
            .refresh-btn {
                background: white;
                color: #667eea;
                border: 2px solid #667eea;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                text-decoration: none;
                display: inline-block;
            }
            .refresh-btn:hover {
                background: #667eea;
                color: white;
            }
            .clear-btn {
                background: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                margin-left: 10px;
            }
            .filters {
                background: rgba(255, 255, 255, 0.2);
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                align-items: center;
            }
            .filter-group {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }
            .filter-group label {
                font-size: 0.9em;
                font-weight: bold;
            }
            .filter-group select {
                padding: 8px 12px;
                border-radius: 5px;
                border: none;
                font-size: 0.9em;
                min-width: 150px;
            }
            .filter-btn {
                background: white;
                color: #667eea;
                border: 2px solid white;
                padding: 8px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                margin-top: 20px;
            }
            .filter-btn:hover {
                background: rgba(255, 255, 255, 0.9);
            }
            .collapsible-section {
                margin-top: 10px;
            }
            .collapsible-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                width: 100%;
                text-align: left;
                margin-top: 5px;
            }
            .collapsible-btn:hover {
                background: #5568d3;
            }
            .collapsible-btn.active {
                background: #764ba2;
            }
            .collapsible-content {
                display: none;
                margin-top: 5px;
            }
            .collapsible-content.active {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔍 Spotive API - Audit Logs</h1>
            <p>Real-time API call monitoring and debugging</p>
            <div>
                <a href="/api/logs" class="refresh-btn">🔄 Refresh</a>
                <a href="/api/logs/clear" class="clear-btn">🗑️ Clear Logs</a>
            </div>
            <form method="get" action="/api/logs" class="filters">
                <div class="filter-group">
                    <label>⏰ Time Filter</label>
                    <select name="time_filter" id="time_filter">
                        <option value="all" """ + ('selected' if time_filter == 'all' else '') + """>All Time</option>
                        <option value="hour" """ + ('selected' if time_filter == 'hour' else '') + """>Last Hour</option>
                        <option value="day" """ + ('selected' if time_filter == 'day' else '') + """>Last 24 Hours</option>
                        <option value="week" """ + ('selected' if time_filter == 'week' else '') + """>Last Week</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>🔗 Endpoint</label>
                    <select name="endpoint" id="endpoint">
                        <option value="all" """ + ('selected' if endpoint == 'all' else '') + """>All Endpoints</option>""" + \
                        ''.join([f'<option value="{ep}" ' + ('selected' if endpoint == ep else '') + f'>{ep}</option>' for ep in unique_endpoints]) + """
                    </select>
                </div>
                <div class="filter-group">
                    <label>✅ Status</label>
                    <select name="status" id="status">
                        <option value="all" """ + ('selected' if status == 'all' else '') + """>All</option>
                        <option value="success" """ + ('selected' if status == 'success' else '') + """>Success Only</option>
                        <option value="failed" """ + ('selected' if status == 'failed' else '') + """>Failed Only</option>
                    </select>
                </div>
                <button type="submit" class="filter-btn">🔍 Apply Filters</button>
            </form>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div>Total Requests</div>
                <div class="stat-value">""" + str(total_logs) + """</div>
            </div>
            <div class="stat-card">
                <div>Success Rate</div>
                <div class="stat-value">""" + str(success_rate) + """%</div>
            </div>
            <div class="stat-card">
                <div>Failed Requests</div>
                <div class="stat-value">""" + str(failed_logs) + """</div>
            </div>
            <div class="stat-card">
                <div>Avg Response Time</div>
                <div class="stat-value">""" + str(avg_duration) + """ms</div>
            </div>
        </div>
        
        <div class="logs-container">
            """ + log_entries_html + """
        </div>
        
        <script>
            // Auto-refresh removed as per user request
            function toggleSection(btn) {
                const content = btn.nextElementSibling;
                const isActive = content.classList.contains('active');
                
                // Close all sections in the same log entry
                const logEntry = btn.closest('.log-entry');
                const allSections = logEntry.querySelectorAll('.collapsible-content');
                const allButtons = logEntry.querySelectorAll('.collapsible-btn');
                
                allSections.forEach(section => section.classList.remove('active'));
                allButtons.forEach(button => button.classList.remove('active'));
                
                // Toggle the clicked section
                if (!isActive) {
                    content.classList.add('active');
                    btn.classList.add('active');
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html_content

@app.get("/api/logs/json")
def get_audit_logs_json():
    """
    Get audit logs as JSON for programmatic access
    """
    return JSONResponse(content={
        "total_logs": len(audit_logs),
        "logs": list(reversed(audit_logs))  # Newest first
    })

@app.get("/api/logs/clear")
def clear_audit_logs():
    """
    Clear all audit logs
    """
    audit_logs.clear()
    return JSONResponse(content={
        "success": True,
        "message": "All audit logs cleared"
    })

@app.get("/api/logs/analytics", response_class=HTMLResponse)
def view_analytics_dashboard(
    time_filter: str = "all",  # all, hour, day, week, custom
    start_date: str = None,
    end_date: str = None,
    endpoint: str = "all",  # all, /api/event/by-interests, /
    status: str = "all",  # all, success, failed
    sort_by: str = "timestamp",  # timestamp, duration, status
    order: str = "desc"  # asc, desc
):
    """
    Advanced analytics dashboard with filters for data scientists
    """
    from datetime import timedelta
    
    # Filter logs based on criteria
    filtered_logs = audit_logs.copy()
    
    # Time filtering
    now = datetime.now()
    if time_filter == "hour":
        cutoff = now - timedelta(hours=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "day":
        cutoff = now - timedelta(days=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "week":
        cutoff = now - timedelta(weeks=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "custom" and start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            filtered_logs = [log for log in filtered_logs 
                            if log.get("timestamp") and start <= datetime.fromisoformat(log["timestamp"]) <= end]
        except:
            pass  # If date parsing fails, show all logs
    
    # Endpoint filtering
    if endpoint != "all":
        filtered_logs = [log for log in filtered_logs if log.get("path") == endpoint]
    
    # Status filtering
    if status == "success":
        filtered_logs = [log for log in filtered_logs if log.get("success", False)]
    elif status == "failed":
        filtered_logs = [log for log in filtered_logs if not log.get("success", True)]
    
    # Sorting
    try:
        if sort_by == "timestamp":
            filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=(order == "desc"))
        elif sort_by == "duration":
            filtered_logs.sort(key=lambda x: x.get("duration_ms", 0), reverse=(order == "desc"))
        elif sort_by == "status":
            filtered_logs.sort(key=lambda x: x.get("success", False), reverse=(order == "desc"))
    except:
        pass  # If sorting fails, return unsorted
    
    # Calculate advanced analytics
    total_filtered = len(filtered_logs)
    successful = sum(1 for log in filtered_logs if log.get("success", False))
    failed = total_filtered - successful
    success_rate = round((successful / total_filtered * 100) if total_filtered > 0 else 0, 2)
    
    durations = [log.get("duration_ms", 0) for log in filtered_logs if log.get("duration_ms") is not None]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
    min_duration = round(min(durations), 2) if durations else 0
    max_duration = round(max(durations), 2) if durations else 0
    median_duration = round(sorted(durations)[len(durations)//2], 2) if durations else 0
    
    # Percentiles
    if durations and len(durations) > 1:
        sorted_durations = sorted(durations)
        p95_duration = round(sorted_durations[int(len(sorted_durations)*0.95)], 2)
        p99_duration = round(sorted_durations[int(len(sorted_durations)*0.99)], 2)
    else:
        p95_duration = 0
        p99_duration = 0
    
    # Endpoint distribution
    endpoint_counts = {}
    for log in filtered_logs:
        path = log.get("path", "unknown")
        endpoint_counts[path] = endpoint_counts.get(path, 0) + 1
    
    # Method distribution
    method_counts = {}
    for log in filtered_logs:
        method = log.get("method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1
    
    # Error analysis
    error_types = {}
    for log in filtered_logs:
        if not log.get("success", True) and log.get("error"):
            error = log.get("error", "Unknown")[:100]  # First 100 chars
            error_types[error] = error_types.get(error, 0) + 1
    
    # Client analysis
    client_ips = {}
    for log in filtered_logs:
        ip = log.get("client_ip", "unknown")
        client_ips[ip] = client_ips.get(ip, 0) + 1
    
    # Time series data (requests per minute)
    time_series = {}
    for log in filtered_logs:
        if log.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(log["timestamp"])
                minute_key = timestamp.strftime("%Y-%m-%d %H:%M")
                time_series[minute_key] = time_series.get(minute_key, 0) + 1
            except:
                pass
    
    # Generate HTML
    return HTMLResponse(content=generate_analytics_html(
        filtered_logs, total_filtered, successful, failed, success_rate,
        avg_duration, min_duration, max_duration, median_duration,
        p95_duration, p99_duration, endpoint_counts, method_counts,
        error_types, client_ips, time_series, time_filter, endpoint, status,
        sort_by, order
    ))

def generate_analytics_html(
    logs, total, successful, failed, success_rate, avg_duration, min_duration,
    max_duration, median_duration, p95, p99, endpoint_counts, method_counts,
    error_types, client_ips, time_series, time_filter, endpoint_filter,
    status_filter, sort_by, order
):
    """Generate advanced analytics HTML"""
    
    # Generate endpoint options
    endpoint_options = ""
    unique_endpoints = set(log.get("path", "") for log in audit_logs if log.get("path"))
    for ep in sorted(unique_endpoints):
        selected = "selected" if ep == endpoint_filter else ""
        endpoint_options += f'<option value="{ep}" {selected}>{ep}</option>'
    
    # Generate log rows
    log_rows = ""
    for i, log in enumerate(logs[:100]):  # Show top 100
        success_icon = "✅" if log.get("success", False) else "❌"
        row_class = "success-row" if log.get("success", False) else "error-row"
        request_body = json.dumps(log.get("request_body", {}), indent=2) if log.get("request_body") else "N/A"
        error_msg = log.get("error", "N/A")
        
        log_rows += f"""
        <tr class="{row_class}">
            <td>{i+1}</td>
            <td>{success_icon}</td>
            <td>{log.get('method', 'N/A')}</td>
            <td>{log.get('path', 'N/A')}</td>
            <td>{log.get('status_code', 'N/A')}</td>
            <td>{log.get('duration_ms', 0):.2f}</td>
            <td>{log.get('timestamp', 'N/A')}</td>
            <td>{log.get('client_ip', 'N/A')}</td>
            <td class="truncate" title="{request_body}">{request_body[:50]}...</td>
            <td class="truncate" title="{error_msg}">{error_msg[:50] if error_msg != 'N/A' else 'N/A'}</td>
        </tr>
        """
    
    # Generate charts data
    endpoint_chart_data = json.dumps([{"name": k, "value": v} for k, v in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]])
    method_chart_data = json.dumps([{"name": k, "value": v} for k, v in method_counts.items()])
    time_series_data = json.dumps([{"time": k, "count": v} for k, v in sorted(time_series.items())])
    
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Spotive API - Advanced Analytics</title>
        <meta charset="UTF-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f5f7fa; padding: 20px; }}
            .container {{ max-width: 1600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
            .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
            .filters {{ background: white; padding: 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .filter-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .filter-group {{ display: flex; flex-direction: column; }}
            .filter-group label {{ font-weight: 600; margin-bottom: 8px; color: #333; }}
            .filter-group select, .filter-group input {{ padding: 10px; border: 2px solid #e1e8ed; border-radius: 6px; font-size: 14px; }}
            .filter-group select:focus, .filter-group input:focus {{ outline: none; border-color: #667eea; }}
            .btn {{ background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }}
            .btn:hover {{ background: #5568d3; }}
            .btn-export {{ background: #2ecc71; margin-left: 10px; }}
            .btn-export:hover {{ background: #27ae60; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .stat-label {{ font-size: 0.9em; color: #666; margin-bottom: 8px; }}
            .stat-value {{ font-size: 2.2em; font-weight: bold; color: #667eea; }}
            .stat-value.success {{ color: #2ecc71; }}
            .stat-value.error {{ color: #e74c3c; }}
            .chart-container {{ background: white; padding: 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .chart-title {{ font-size: 1.3em; font-weight: 600; margin-bottom: 20px; color: #333; }}
            .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
            .table-container {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #667eea; color: white; padding: 15px; text-align: left; font-weight: 600; }}
            td {{ padding: 12px 15px; border-bottom: 1px solid #e1e8ed; }}
            .success-row {{ background: #d4edda; }}
            .error-row {{ background: #f8d7da; }}
            tr:hover {{ background: #f8f9fa; }}
            .truncate {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }}
            .chart-bar {{ background: #667eea; height: 30px; margin: 5px 0; display: flex; align-items: center; padding-left: 10px; color: white; border-radius: 4px; }}
            .distribution-item {{ display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #e1e8ed; }}
            .distribution-item:hover {{ background: #f8f9fa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Advanced Analytics Dashboard</h1>
                <p>Data Science & Performance Analytics</p>
            </div>

            <div class="filters">
                <form method="get" action="/api/logs/analytics">
                    <div class="filter-grid">
                        <div class="filter-group">
                            <label>Time Range</label>
                            <select name="time_filter" id="timeFilter">
                                <option value="all" {'selected' if time_filter == 'all' else ''}>All Time</option>
                                <option value="hour" {'selected' if time_filter == 'hour' else ''}>Past Hour</option>
                                <option value="day" {'selected' if time_filter == 'day' else ''}>Past 24 Hours</option>
                                <option value="week" {'selected' if time_filter == 'week' else ''}>Past Week</option>
                                <option value="custom" {'selected' if time_filter == 'custom' else ''}>Custom Range</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>Endpoint</label>
                            <select name="endpoint">
                                <option value="all">All Endpoints</option>
                                {endpoint_options}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>Status</label>
                            <select name="status">
                                <option value="all" {'selected' if status_filter == 'all' else ''}>All</option>
                                <option value="success" {'selected' if status_filter == 'success' else ''}>Success Only</option>
                                <option value="failed" {'selected' if status_filter == 'failed' else ''}>Failed Only</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>Sort By</label>
                            <select name="sort_by">
                                <option value="timestamp" {'selected' if sort_by == 'timestamp' else ''}>Timestamp</option>
                                <option value="duration" {'selected' if sort_by == 'duration' else ''}>Duration</option>
                                <option value="status" {'selected' if sort_by == 'status' else ''}>Status</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>Order</label>
                            <select name="order">
                                <option value="desc" {'selected' if order == 'desc' else ''}>Descending</option>
                                <option value="asc" {'selected' if order == 'asc' else ''}>Ascending</option>
                            </select>
                        </div>
                    </div>
                    <div class="filter-grid" id="customDates" style="display: {'block' if time_filter == 'custom' else 'none'};">
                        <div class="filter-group">
                            <label>Start Date</label>
                            <input type="datetime-local" name="start_date">
                        </div>
                        <div class="filter-group">
                            <label>End Date</label>
                            <input type="datetime-local" name="end_date">
                        </div>
                    </div>
                    <button type="submit" class="btn">🔍 Apply Filters</button>
                    <button type="button" class="btn btn-export" onclick="exportToCSV()">📥 Export CSV</button>
                </form>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Requests</div>
                    <div class="stat-value">{total}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Successful</div>
                    <div class="stat-value success">{successful}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value error">{failed}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Success Rate</div>
                    <div class="stat-value">{success_rate}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Avg Response Time</div>
                    <div class="stat-value">{avg_duration}ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Min Response Time</div>
                    <div class="stat-value">{min_duration}ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Max Response Time</div>
                    <div class="stat-value">{max_duration}ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Median Response Time</div>
                    <div class="stat-value">{median_duration}ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">P95 Response Time</div>
                    <div class="stat-value">{p95}ms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">P99 Response Time</div>
                    <div class="stat-value">{p99}ms</div>
                </div>
            </div>

            <div class="chart-grid">
                <div class="chart-container">
                    <div class="chart-title">📍 Top Endpoints</div>
                    {"".join([f'<div class="distribution-item"><span>{k}</span><strong>{v} requests</strong></div>' for k, v in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]])}
                </div>
                <div class="chart-container">
                    <div class="chart-title">🔧 HTTP Methods</div>
                    {"".join([f'<div class="distribution-item"><span>{k}</span><strong>{v} requests</strong></div>' for k, v in sorted(method_counts.items(), key=lambda x: x[1], reverse=True)])}
                </div>
            </div>

            {"<div class='chart-container'><div class='chart-title'>⚠️ Top Errors</div>" + "".join([f'<div class="distribution-item"><span class="truncate" title="{k}">{k[:80]}</span><strong>{v} times</strong></div>' for k, v in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]]) + "</div>" if error_types else ""}

            <div class="chart-container">
                <div class="chart-title">👥 Top Clients</div>
                {"".join([f'<div class="distribution-item"><span>{k}</span><strong>{v} requests</strong></div>' for k, v in sorted(client_ips.items(), key=lambda x: x[1], reverse=True)[:10]])}
            </div>

            <div class="table-container">
                <h2 class="chart-title">📋 Detailed Logs (Top 100)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Status</th>
                            <th>Method</th>
                            <th>Endpoint</th>
                            <th>Code</th>
                            <th>Duration (ms)</th>
                            <th>Timestamp</th>
                            <th>Client IP</th>
                            <th>Request Body</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody>
                        {log_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            document.getElementById('timeFilter').addEventListener('change', function() {{
                document.getElementById('customDates').style.display = 
                    this.value === 'custom' ? 'block' : 'none';
            }});

            function exportToCSV() {{
                window.location.href = '/api/logs/export?time_filter={time_filter}&endpoint={endpoint_filter}&status={status_filter}';
            }}
            
            // Removed auto-refresh as per user request
        </script>
    </body>
    </html>
    """
    
    return html

@app.get("/api/logs/export")
def export_logs_csv(
    time_filter: str = "all",
    endpoint: str = "all",
    status: str = "all"
):
    """Export filtered logs as CSV for data analysis"""
    from datetime import timedelta
    import csv
    from io import StringIO
    
    # Apply same filtering logic
    filtered_logs = audit_logs.copy()
    
    # Time filtering
    now = datetime.now()
    if time_filter == "hour":
        cutoff = now - timedelta(hours=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "day":
        cutoff = now - timedelta(days=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    elif time_filter == "week":
        cutoff = now - timedelta(weeks=1)
        filtered_logs = [log for log in filtered_logs if log.get("timestamp") and datetime.fromisoformat(log["timestamp"]) > cutoff]
    
    if endpoint != "all":
        filtered_logs = [log for log in filtered_logs if log.get("path") == endpoint]
    
    if status == "success":
        filtered_logs = [log for log in filtered_logs if log.get("success", False)]
    elif status == "failed":
        filtered_logs = [log for log in filtered_logs if not log.get("success", True)]
    
    # Create CSV
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'timestamp', 'method', 'path', 'status_code', 'duration_ms',
        'success', 'client_ip', 'user_agent', 'request_body', 'error'
    ])
    writer.writeheader()
    
    for log in filtered_logs:
        writer.writerow({
            'timestamp': log.get('timestamp', ''),
            'method': log.get('method', ''),
            'path': log.get('path', ''),
            'status_code': log.get('status_code', ''),
            'duration_ms': log.get('duration_ms', 0),
            'success': log.get('success', False),
            'client_ip': log.get('client_ip', ''),
            'user_agent': log.get('user_agent', ''),
            'request_body': json.dumps(log.get('request_body', {})),
            'error': log.get('error', '')
        })
    
    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=spotive_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )