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
from datetime import datetime
from typing import List, Dict, Any
import asyncio
import time
from app.core.config import settings

app = FastAPI(
    title="Spotive API",
    description="AI-Powered Event Discovery API for Bangalore",
    version="0.1.0 (MVP)"
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

**Predefined Categories (ONLY use these exactly):**
- concert (music events, live performances, DJ nights, music festivals, bands, singing)
- sports (marathons, cricket, football, fitness events, gym, exercise, running)
- outdoor (trekking, hiking, nature activities, adventure sports, camping, cycling)
- food (food festivals, buffet events, culinary experiences, dining, gastronomy)
- spiritual (religious events, meditation, temple visits, spiritual gatherings, devotional)
- cultural (art exhibitions, theater, dance performances, traditional events, heritage, museums)
- kids (children activities, family events, kids workshops, family-friendly)
- entertainment (general entertainment, movies, games, leisure, shows)
- comedy (standup comedy, comedy shows, humor, laughter)

**CRITICAL RULES:**
1. Return ONLY categories that ACTUALLY match the user's interests
2. Do NOT return all categories - be selective!
3. Maximum 3 categories per response
4. If only one category matches, return only that one
5. Return ONLY a JSON array of category names
6. Use EXACT category names from the list above

**Examples (Follow these patterns - BE SELECTIVE!):**
- "comedy" → ["comedy"]
- "standup" → ["comedy"]
- "music" → ["concert"]
- "trekking" → ["outdoor"]
- "food" → ["food"]
- "meditation" → ["spiritual"]
- "kids" → ["kids"]
- "music, dancing" → ["concert"]
- "family fun" → ["kids"]
- "adventure, nature" → ["outdoor"]
- "food, traditional" → ["food", "cultural"]
- "fitness, gym" → ["sports"]
- "comedy, music" → ["comedy", "concert"]

**DO NOT return all 8 categories - only return what matches!**
"""),
    ("human", "User interests: {interests}\n\nReturn ONLY the JSON array of matching categories (max 3):")
])

# Pydantic models for requests and responses
class InterestsRequest(BaseModel):
    interests: str  # Comma-separated interests
    phone_number: str = None  # Optional: for personalized recommendations
    hotel_id: str = None  # Optional: filter events by hotel location
    
    class Config:
        json_schema_extra = {
            "example": {
                "interests": "music, outdoor, adventure",
                "phone_number": "+919876543210",
                "hotel_id": "marriott-bangalore"
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
    preferred_locations: List[str] = None
    preferred_time_slots: List[str] = None
    price_range: Dict[str, int] = None
    avoid_categories: List[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "preferred_categories": ["comedy", "outdoor"],
                "preferred_locations": ["Indiranagar", "Koramangala"],
                "preferred_time_slots": ["evening", "weekend"],
                "price_range": {"min": 0, "max": 1500},
                "avoid_categories": ["spiritual"]
            }
        }

class DiscoverEventsRequest(BaseModel):
    interests: str = None  # Optional: can use profile only if empty
    
    class Config:
        json_schema_extra = {
            "example": {
                "interests": "comedy"
            }
        }

# ==================== HOTEL MANAGEMENT MODELS ====================

class HotelCreate(BaseModel):
    name: str
    slug: str  # URL-friendly identifier
    location_city: str
    location_area: str = None
    address: str = None
    country_code: str = "IN"
    timezone: str = "Asia/Kolkata"
    logo_url: str = None
    brand_colors: Dict[str, str] = {"primary": "#000000", "secondary": "#FFFFFF"}
    theme_config: Dict[str, Any] = {}
    latitude: float = None
    longitude: float = None
    search_radius_km: int = 10
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Taj Wellington Mews",
                "slug": "taj-mumbai",
                "location_city": "Mumbai",
                "location_area": "Colaba",
                "address": "123 MG Road, Mumbai",
                "logo_url": "https://example.com/logo.png",
                "brand_colors": {
                    "primary": "#C4A962",
                    "secondary": "#1A1A1A"
                },
                "latitude": 18.9220,
                "longitude": 72.8347,
                "search_radius_km": 15
            }
        }

class HotelUpdate(BaseModel):
    name: str = None
    location_city: str = None
    location_area: str = None
    address: str = None
    logo_url: str = None
    brand_colors: Dict[str, str] = None
    theme_config: Dict[str, Any] = None
    latitude: float = None
    longitude: float = None
    search_radius_km: int = None
    is_active: bool = None
    metadata: Dict[str, Any] = None

class HotelServiceCreate(BaseModel):
    service_type: str  # spa, restaurant, bar, tour, cab, etc.
    name: str
    description: str = None
    short_description: str = None
    price_range: str = None
    price_min: float = None
    price_max: float = None
    currency: str = "INR"
    available_hours: str = None
    image_url: str = None
    booking_link: str = None
    phone_number: str = None
    is_featured: bool = False
    display_order: int = 0
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_type": "spa",
                "name": "Jiva Spa",
                "short_description": "Rejuvenating spa treatments",
                "description": "Experience traditional Indian wellness...",
                "price_range": "₹3000 - ₹8000",
                "price_min": 3000,
                "price_max": 8000,
                "available_hours": "10:00 AM - 10:00 PM",
                "image_url": "https://example.com/spa.jpg",
                "booking_link": "https://hotel.com/spa",
                "phone_number": "+912212345678",
                "is_featured": True,
                "display_order": 1
            }
        }

class HotelServiceUpdate(BaseModel):
    service_type: str = None
    name: str = None
    description: str = None
    short_description: str = None
    price_range: str = None
    price_min: float = None
    price_max: float = None
    available_hours: str = None
    image_url: str = None
    booking_link: str = None
    phone_number: str = None
    is_featured: bool = None
    display_order: int = None
    is_active: bool = None
    metadata: Dict[str, Any] = None

# Helper functions for user management and hotel operations
import re
from math import radians, cos, sin, asin, sqrt

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

def track_user_search(phone_number: str, interests: str, mapped_categories: list, results_count: int):
    """Track user search and accumulate preferences"""
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
            "search_query": interests,
            "mapped_categories": mapped_categories,
            "search_timestamp": datetime.now().isoformat(),
            "results_count": results_count
        }
        supabase.table('user_search_history').insert(search_entry).execute()
        
        # Update user's favorite_categories (accumulate preferences)
        favorite_categories = user.get('favorite_categories', {})
        if not isinstance(favorite_categories, dict):
            favorite_categories = {}
        
        for category in mapped_categories:
            favorite_categories[category] = favorite_categories.get(category, 0) + 1
        
        # Update user record
        supabase.table('users').update({
            "favorite_categories": favorite_categories,
            "total_searches": user.get('total_searches', 0) + 1,
            "last_active": datetime.now().isoformat()
        }).eq('phone_number', phone_number).execute()
        
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

def get_hotel_by_id_or_slug(hotel_id: str) -> Dict[str, Any]:
    """Get hotel details by ID or slug"""
    try:
        # Try by ID first
        result = supabase.table('hotels').select("*").eq('id', hotel_id).execute()
        
        # If not found, try by slug
        if not result.data:
            result = supabase.table('hotels').select("*").eq('slug', hotel_id).execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error getting hotel: {e}")
        return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula
    Returns distance in kilometers
    """
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    
    return c * r

def filter_events_by_hotel_location(events: List[Dict], hotel: Dict[str, Any]) -> List[Dict]:
    """
    Filter and sort events based on hotel location and search radius
    Returns events within radius, sorted by distance
    """
    if not hotel:
        return events
    
    hotel_lat = hotel.get('latitude')
    hotel_lon = hotel.get('longitude')
    hotel_city = hotel.get('location_city', '').lower()
    search_radius = hotel.get('search_radius_km', 10)
    
    filtered_events = []
    
    for event in events:
        # If hotel has coordinates and event has coordinates, use distance
        event_lat = event.get('latitude')
        event_lon = event.get('longitude')
        
        if hotel_lat and hotel_lon and event_lat and event_lon:
            distance = calculate_distance(hotel_lat, hotel_lon, event_lat, event_lon)
            if distance <= search_radius:
                event['distance_km'] = round(distance, 2)
                filtered_events.append(event)
        else:
            # Fallback: Filter by city name
            event_location = event.get('location', '').lower()
            if hotel_city in event_location or 'bangalore' in event_location:
                event['distance_km'] = None  # Unknown distance
                filtered_events.append(event)
    
    # Sort by distance (closest first), events without distance go to end
    filtered_events.sort(key=lambda x: x.get('distance_km') if x.get('distance_km') is not None else float('inf'))
    
    return filtered_events

def get_hotel_services_as_events(hotel_id: str, categories: List[str]) -> List[Dict]:
    """
    Get hotel services and format them as event objects
    Matches services to requested categories
    """
    try:
        # Get hotel
        hotel = get_hotel_by_id_or_slug(hotel_id)
        if not hotel:
            return []
        
        actual_hotel_id = hotel['id']
        
        # Get all active services for the hotel
        services_response = supabase.table('hotel_services')\
            .select("*")\
            .eq('hotel_id', actual_hotel_id)\
            .eq('is_active', True)\
            .order('is_featured', desc=True)\
            .order('display_order')\
            .execute()
        
        if not services_response.data:
            return []
        
        # Map service types to event categories
        service_to_category_map = {
            'spa': 'entertainment',
            'restaurant': 'food',
            'bar': 'entertainment',
            'gym': 'sports',
            'pool': 'outdoor',
            'tour': 'outdoor',
            'cab': 'entertainment',
            'room_service': 'food'
        }
        
        # Convert services to event format
        service_events = []
        for service in services_response.data:
            service_type = service.get('service_type', '')
            category = service_to_category_map.get(service_type, 'entertainment')
            
            # Only include if matches requested categories
            if categories and category not in categories:
                continue
            
            # Format as event object
            service_event = {
                'id': service.get('id'),
                'name': service.get('name'),
                'category': category,
                'description': service.get('description') or service.get('short_description', ''),
                'location': f"{hotel.get('name')} - {hotel.get('location_area', hotel.get('location_city'))}",
                'date': 'Available daily',
                'time': service.get('available_hours', 'Contact hotel'),
                'price': service.get('price_range', 'See hotel for pricing'),
                'image_url': service.get('image_url'),
                'booking_link': service.get('booking_link'),
                'is_hotel_service': True,
                'service_type': service_type,
                'hotel_id': actual_hotel_id,
                'distance_km': 0,  # Hotel services are at 0 distance
                'is_featured': service.get('is_featured', False)
            }
            service_events.append(service_event)
        
        return service_events
    except Exception as e:
        print(f"Error getting hotel services: {e}")
        return []

# Keyword-based category matching as fallback
def keyword_match_categories(interests: str, valid_categories: list) -> list:
    """
    Fallback keyword matching when LLM fails
    Maps interests to categories using keyword matching
    """
    interests_lower = interests.lower()
    matched = []
    
    # Keyword mappings - must align with database categories
    keyword_map = {
        "concert": ["music", "concert", "band", "dj", "singing", "song", "live music", "performance", "festival"],
        "sports": ["sport", "fitness", "exercise", "gym", "marathon", "running", "cricket", "football", "game", "athletic"],
        "outdoor": ["outdoor", "trek", "hike", "nature", "adventure", "camping", "cycling", "mountain", "trail"],
        "food": ["food", "buffet", "culinary", "dining", "cuisine", "feast", "gastronomy", "eat"],
        "spiritual": ["spiritual", "meditation", "temple", "religious", "prayer", "worship", "devotion", "peace", "mandir"],
        "cultural": ["cultural", "art", "theater", "theatre", "dance", "traditional", "heritage", "museum", "exhibition", "classical"],
        "kids": ["kid", "child", "children", "family", "family-friendly"],
        "entertainment": ["entertainment", "show", "movie", "film", "leisure", "general fun"],
        "comedy": ["comedy", "standup", "stand-up", "humor", "laugh", "comic", "comedian", "funny"],
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
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    # Capture request body for POST requests
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                log_entry["request_body"] = json.loads(body.decode())
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
    except Exception as e:
        log_entry["status_code"] = 500
        log_entry["success"] = False
        log_entry["error"] = str(e)
        log_entry["error_type"] = type(e).__name__
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

@app.post("/api/hotels")
def create_hotel(hotel: HotelCreate):
    """
    Create a new hotel in the system
    
    Request body:
    - name: Hotel name
    - slug: URL-friendly identifier (must be unique)
    - location_city: City where hotel is located
    - location_area: Specific area/neighborhood
    - brand_colors: Primary and secondary colors
    - logo_url: URL to hotel logo
    - search_radius_km: Default search radius for events
    
    Returns the created hotel with ID
    """
    try:
        # Check if slug already exists
        existing = supabase.table('hotels').select("id").eq('slug', hotel.slug).execute()
        if existing.data:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Hotel with slug '{hotel.slug}' already exists"
                }
            )
        
        # Prepare hotel data
        hotel_data = {
            "name": hotel.name,
            "slug": hotel.slug,
            "location_city": hotel.location_city,
            "location_area": hotel.location_area,
            "address": hotel.address,
            "country_code": hotel.country_code,
            "timezone": hotel.timezone,
            "logo_url": hotel.logo_url,
            "brand_colors": hotel.brand_colors,
            "theme_config": hotel.theme_config,
            "latitude": hotel.latitude,
            "longitude": hotel.longitude,
            "search_radius_km": hotel.search_radius_km,
            "metadata": hotel.metadata,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert hotel
        result = supabase.table('hotels').insert(hotel_data).execute()
        
        return JSONResponse(content={
            "success": True,
            "message": "Hotel created successfully",
            "hotel": result.data[0] if result.data else hotel_data
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/hotels")
def list_hotels(is_active: bool = None):
    """
    List all hotels in the system
    
    Query parameters:
    - is_active: Filter by active status (optional)
    
    Returns list of all hotels
    """
    try:
        query = supabase.table('hotels').select("*")
        
        if is_active is not None:
            query = query.eq('is_active', is_active)
        
        result = query.order('created_at', desc=True).execute()
        
        return JSONResponse(content={
            "success": True,
            "count": len(result.data) if result.data else 0,
            "hotels": result.data if result.data else []
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/hotels/{hotel_id}")
def get_hotel(hotel_id: str):
    """
    Get hotel details by ID or slug
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    
    Returns complete hotel information
    """
    try:
        # Try to get by ID first
        result = supabase.table('hotels').select("*").eq('id', hotel_id).execute()
        
        # If not found, try by slug
        if not result.data:
            result = supabase.table('hotels').select("*").eq('slug', hotel_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "hotel": result.data[0]
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.put("/api/hotels/{hotel_id}")
def update_hotel(hotel_id: str, hotel: HotelUpdate):
    """
    Update hotel information
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    
    Request body: All fields are optional, only provided fields will be updated
    """
    try:
        # Check if hotel exists
        existing = supabase.table('hotels').select("id").eq('id', hotel_id).execute()
        if not existing.data:
            existing = supabase.table('hotels').select("id").eq('slug', hotel_id).execute()
        
        if not existing.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        actual_hotel_id = existing.data[0]['id']
        
        # Prepare update data (only non-None fields)
        update_data = {}
        if hotel.name is not None:
            update_data['name'] = hotel.name
        if hotel.location_city is not None:
            update_data['location_city'] = hotel.location_city
        if hotel.location_area is not None:
            update_data['location_area'] = hotel.location_area
        if hotel.address is not None:
            update_data['address'] = hotel.address
        if hotel.logo_url is not None:
            update_data['logo_url'] = hotel.logo_url
        if hotel.brand_colors is not None:
            update_data['brand_colors'] = hotel.brand_colors
        if hotel.theme_config is not None:
            update_data['theme_config'] = hotel.theme_config
        if hotel.latitude is not None:
            update_data['latitude'] = hotel.latitude
        if hotel.longitude is not None:
            update_data['longitude'] = hotel.longitude
        if hotel.search_radius_km is not None:
            update_data['search_radius_km'] = hotel.search_radius_km
        if hotel.is_active is not None:
            update_data['is_active'] = hotel.is_active
        if hotel.metadata is not None:
            update_data['metadata'] = hotel.metadata
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        # Update hotel
        result = supabase.table('hotels').update(update_data).eq('id', actual_hotel_id).execute()
        
        return JSONResponse(content={
            "success": True,
            "message": "Hotel updated successfully",
            "hotel": result.data[0] if result.data else update_data
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.delete("/api/hotels/{hotel_id}")
def delete_hotel(hotel_id: str):
    """
    Delete a hotel (soft delete by setting is_active=false)
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    """
    try:
        # Update is_active to false instead of hard delete
        result = supabase.table('hotels').update({
            "is_active": False,
            "updated_at": datetime.now().isoformat()
        }).eq('id', hotel_id).execute()
        
        if not result.data:
            result = supabase.table('hotels').update({
                "is_active": False,
                "updated_at": datetime.now().isoformat()
            }).eq('slug', hotel_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "message": "Hotel deactivated successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/hotels/{hotel_id}/config")
def get_hotel_config(hotel_id: str):
    """
    Get hotel configuration for kiosk frontend
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    
    Returns hotel branding, location settings, and configuration
    """
    try:
        # Get hotel by ID or slug
        result = supabase.table('hotels').select("*").eq('id', hotel_id).execute()
        if not result.data:
            result = supabase.table('hotels').select("*").eq('slug', hotel_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        hotel = result.data[0]
        
        # Return configuration optimized for frontend
        return JSONResponse(content={
            "success": True,
            "config": {
                "hotel_id": hotel['id'],
                "hotel_name": hotel['name'],
                "slug": hotel['slug'],
                "branding": {
                    "logo_url": hotel.get('logo_url'),
                    "brand_colors": hotel.get('brand_colors', {}),
                    "theme_config": hotel.get('theme_config', {})
                },
                "location": {
                    "city": hotel['location_city'],
                    "area": hotel.get('location_area'),
                    "address": hotel.get('address'),
                    "latitude": hotel.get('latitude'),
                    "longitude": hotel.get('longitude'),
                    "search_radius_km": hotel.get('search_radius_km', 10)
                },
                "settings": {
                    "timezone": hotel.get('timezone', 'Asia/Kolkata'),
                    "country_code": hotel.get('country_code', 'IN'),
                    "is_active": hotel.get('is_active', True)
                }
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

# ==================== HOTEL SERVICES ENDPOINTS ====================

@app.post("/api/hotels/{hotel_id}/services")
def create_hotel_service(hotel_id: str, service: HotelServiceCreate):
    """
    Create a new service for a hotel (spa, restaurant, bar, etc.)
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    
    Request body: Service details including type, name, pricing, etc.
    """
    try:
        # Verify hotel exists
        hotel_result = supabase.table('hotels').select("id").eq('id', hotel_id).execute()
        if not hotel_result.data:
            hotel_result = supabase.table('hotels').select("id").eq('slug', hotel_id).execute()
        
        if not hotel_result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        actual_hotel_id = hotel_result.data[0]['id']
        
        # Prepare service data
        service_data = {
            "hotel_id": actual_hotel_id,
            "service_type": service.service_type,
            "name": service.name,
            "description": service.description,
            "short_description": service.short_description,
            "price_range": service.price_range,
            "price_min": service.price_min,
            "price_max": service.price_max,
            "currency": service.currency,
            "available_hours": service.available_hours,
            "image_url": service.image_url,
            "booking_link": service.booking_link,
            "phone_number": service.phone_number,
            "is_featured": service.is_featured,
            "display_order": service.display_order,
            "metadata": service.metadata,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert service
        result = supabase.table('hotel_services').insert(service_data).execute()
        
        return JSONResponse(content={
            "success": True,
            "message": "Service created successfully",
            "service": result.data[0] if result.data else service_data
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/hotels/{hotel_id}/services")
def list_hotel_services(hotel_id: str, service_type: str = None, is_featured: bool = None, is_active: bool = True):
    """
    List all services for a hotel
    
    Path parameter:
    - hotel_id: Hotel UUID or slug
    
    Query parameters:
    - service_type: Filter by service type (spa, restaurant, bar, etc.)
    - is_featured: Filter by featured status
    - is_active: Filter by active status (default: true)
    
    Returns list of hotel services
    """
    try:
        # Get hotel ID
        hotel_result = supabase.table('hotels').select("id").eq('id', hotel_id).execute()
        if not hotel_result.data:
            hotel_result = supabase.table('hotels').select("id").eq('slug', hotel_id).execute()
        
        if not hotel_result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Hotel not found"
                }
            )
        
        actual_hotel_id = hotel_result.data[0]['id']
        
        # Build query
        query = supabase.table('hotel_services').select("*").eq('hotel_id', actual_hotel_id)
        
        if service_type:
            query = query.eq('service_type', service_type)
        if is_featured is not None:
            query = query.eq('is_featured', is_featured)
        if is_active is not None:
            query = query.eq('is_active', is_active)
        
        result = query.order('display_order').order('created_at', desc=True).execute()
        
        return JSONResponse(content={
            "success": True,
            "count": len(result.data) if result.data else 0,
            "services": result.data if result.data else []
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.put("/api/hotels/{hotel_id}/services/{service_id}")
def update_hotel_service(hotel_id: str, service_id: str, service: HotelServiceUpdate):
    """
    Update a hotel service
    
    Path parameters:
    - hotel_id: Hotel UUID or slug
    - service_id: Service UUID
    
    Request body: All fields are optional
    """
    try:
        # Prepare update data
        update_data = {}
        if service.service_type is not None:
            update_data['service_type'] = service.service_type
        if service.name is not None:
            update_data['name'] = service.name
        if service.description is not None:
            update_data['description'] = service.description
        if service.short_description is not None:
            update_data['short_description'] = service.short_description
        if service.price_range is not None:
            update_data['price_range'] = service.price_range
        if service.price_min is not None:
            update_data['price_min'] = service.price_min
        if service.price_max is not None:
            update_data['price_max'] = service.price_max
        if service.available_hours is not None:
            update_data['available_hours'] = service.available_hours
        if service.image_url is not None:
            update_data['image_url'] = service.image_url
        if service.booking_link is not None:
            update_data['booking_link'] = service.booking_link
        if service.phone_number is not None:
            update_data['phone_number'] = service.phone_number
        if service.is_featured is not None:
            update_data['is_featured'] = service.is_featured
        if service.display_order is not None:
            update_data['display_order'] = service.display_order
        if service.is_active is not None:
            update_data['is_active'] = service.is_active
        if service.metadata is not None:
            update_data['metadata'] = service.metadata
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        # Update service
        result = supabase.table('hotel_services').update(update_data).eq('id', service_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Service not found"
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "message": "Service updated successfully",
            "service": result.data[0]
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.delete("/api/hotels/{hotel_id}/services/{service_id}")
def delete_hotel_service(hotel_id: str, service_id: str):
    """
    Delete a hotel service (soft delete)
    
    Path parameters:
    - hotel_id: Hotel UUID or slug
    - service_id: Service UUID
    """
    try:
        result = supabase.table('hotel_services').update({
            "is_active": False,
            "updated_at": datetime.now().isoformat()
        }).eq('id', service_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Service not found"
                }
            )
        
        return JSONResponse(content={
            "success": True,
            "message": "Service deactivated successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

# ==================== USER MANAGEMENT ENDPOINTS ====================

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

@app.post("/api/users/{phone_number}/discover-events")
def discover_events_personalized(phone_number: str, request: DiscoverEventsRequest, background_tasks: BackgroundTasks, req: Request):
    """
    Discover events with personalization based on user profile
    
    Path parameter:
    - phone_number: User's phone number
    
    Request body:
    - interests: Optional comma-separated interests. If empty, uses user's profile
    
    This endpoint combines user's search with their accumulated preferences for better recommendations
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
        
        # Use the same logic as /api/event/by-interests
        valid_categories = ["concert", "sports", "outdoor", "food", "spiritual", "cultural", "kids", "entertainment", "comedy"]
        
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
                    "message": "Could not map interests to event categories",
                    "hint": "Try: music, comedy, sports, outdoor, food"
                }
            )
        
        # Query events
        events = []
        for category in categories:
            response = supabase.table('events').select("*").eq('category', category).execute()
            if response.data:
                events.extend(response.data)
        
        if not events:
            # Track search
            track_user_search(phone_number, combined_interests, categories, 0)
            
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No events found matching your interests"
                }
            )
        
        # Select up to 5 events
        selected_events = events[:5] if len(events) > 5 else events
        
        # Generate conversational descriptions
        events_with_suggestions = []
        
        for event in selected_events:
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
                except:
                    suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}!"
            else:
                suggestion = f"Check out {event.get('name', 'this event')} at {event.get('location', 'Bangalore')}!"
            
            events_with_suggestions.append({
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
                }
            })
        
        # Track search (accumulate preferences)
        track_user_search(phone_number, combined_interests, categories, len(events))
        
        return JSONResponse(content={
            "success": True,
            "personalized": True,
            "user_top_categories": user_top_categories,
            "original_interests": request.interests,
            "combined_interests_used": combined_interests,
            "mapped_categories": categories,
            "mapping_method": mapping_method,
            "total_matching_events": len(events),
            "returned_events": len(events_with_suggestions),
            "events": events_with_suggestions,
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

@app.post("/api/event/by-interests")
def get_event_by_interests(
    request: InterestsRequest, 
    background_tasks: BackgroundTasks, 
    req: Request
):
    """
    Get events based on user interests with optional hotel-specific filtering.
    
    Request body:
    - interests: Comma-separated interests (e.g., "music, outdoor, adventure")
    - phone_number: Phone number for real-time results and tracking (+91XXXXXXXXXX or international)
    - hotel_id: Optional hotel ID or slug for location-based filtering
    
    The system will:
    1. Use AI to map interests to event categories
    2. Query events matching those categories
    3. If hotel_id provided:
       - Prioritize hotel's own services (spa, restaurant, bar)
       - Filter external events by hotel location and search radius
       - Sort by distance from hotel
    4. Return up to 5 matching events with conversational descriptions
    5. If phone_number provided:
       - Track search history and accumulate preferences
       - Write results to kiosk_results table for real-time push to frontend
       - Frontend subscribes to phone_number to receive results instantly
    
    NOTE: For full personalization features, use /api/users/{phone_number}/discover-events
    """
    start_time = datetime.now()
    try:
        # Predefined categories (must match database exactly)
        # Note: Database has both "entertainment" and "comedy" as separate categories
        valid_categories = ["concert", "sports", "outdoor", "food", "spiritual", "cultural", "kids", "entertainment", "comedy"]
        
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
                    "message": f"Could not map interests '{request.interests}' to any event categories. Please try different interests.",
                    "valid_categories": valid_categories,
                    "hint": "Try: music, comedy, sports, outdoor, food, spiritual, cultural, kids"
                }
            )
        
        # Step 2: Query Supabase for events matching any of the categories
        # Build OR query for multiple categories
        events = []
        for category in categories:
            response = supabase.table('events').select("*").eq('category', category).execute()
            if response.data:
                events.extend(response.data)
        
        # Step 2.5: Hotel-specific filtering (if hotel_id provided)
        hotel = None
        hotel_services = []
        if request.hotel_id:
            print(f"DEBUG - Filtering events for hotel: {request.hotel_id}")
            hotel = get_hotel_by_id_or_slug(request.hotel_id)
            
            if hotel:
                # Get hotel services first (priority)
                hotel_services = get_hotel_services_as_events(request.hotel_id, categories)
                print(f"DEBUG - Found {len(hotel_services)} hotel services matching categories")
                
                # Filter external events by hotel location
                events = filter_events_by_hotel_location(events, hotel)
                print(f"DEBUG - After location filtering: {len(events)} external events")
                
                # Combine: Hotel services first, then nearby events
                events = hotel_services + events
            else:
                print(f"DEBUG - Hotel not found: {request.hotel_id}")
        
        if not events or len(events) == 0:
            # Log to Supabase (async)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            background_tasks.add_task(log_to_supabase, {
                "timestamp": datetime.now().isoformat(),
                "endpoint": "/api/event/by-interests",
                "interests": request.interests,
                "mapped_categories": json.dumps(categories),
                "mapping_method": mapping_method,
                "total_matching_events": 0,
                "selected_event_id": None,
                "selected_event_name": None,
                "selected_event_category": None,
                "success": False,
                "error_message": f"No events found matching interests: {request.interests}",
                "response_time_ms": response_time,
                "client_ip": req.client.host if req.client else "unknown",
                "user_agent": req.headers.get("user-agent", "unknown")
            })
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No events found matching interests: {request.interests}",
                    "mapped_categories": categories
                }
            )
        
        # Step 3: Select up to 5 events (or all if less than 5)
        selected_events = events[:5] if len(events) > 5 else events
        
        # Step 4: Generate conversational descriptions for each event
        events_with_suggestions = []
        
        for event in selected_events:
            # Generate conversational description if LLM is available
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
            
            event_details = {
                "id": event.get("id"),
                "name": event.get("name"),
                "category": event.get("category"),
                "location": event.get("location"),
                "date": event.get("date"),
                "time": event.get("time"),
                "price": event.get("price"),
                "image_url": event.get("image_url"),
                "booking_link": event.get("booking_link")
            }
            
            # Add hotel-specific fields if hotel_id was provided
            if request.hotel_id:
                event_details["is_hotel_service"] = event.get("is_hotel_service", False)
                event_details["distance_km"] = event.get("distance_km")
                if event.get("is_hotel_service"):
                    event_details["service_type"] = event.get("service_type")
            
            events_with_suggestions.append({
                "suggestion": suggestion,
                "event_details": event_details
            })
        
        # Track user search if phone_number provided (optional)
        if request.phone_number:
            if validate_phone_number(request.phone_number):
                # Get or create user and track search
                user = get_or_create_user(request.phone_number)
                if user:
                    background_tasks.add_task(track_user_search, request.phone_number, request.interests, categories, len(events))
        
        # Log to Supabase (async) - SUCCESS CASE
        # Log the first event for analytics purposes
        first_event = selected_events[0]
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/event/by-interests",
            "interests": request.interests,
            "mapped_categories": json.dumps(categories),
            "mapping_method": mapping_method,  # Track which method was used
            "total_matching_events": len(events),
            "selected_event_id": first_event.get("id"),
            "selected_event_name": first_event.get("name"),
            "selected_event_category": first_event.get("category"),
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
            "mapping_method": mapping_method,  # "llm" or "keyword_fallback"
            "total_matching_events": len(events),
            "returned_events": len(events_with_suggestions),
            "events": events_with_suggestions,
            "source": "Supabase",
            "ai_generated": llm_available,
            "personalized": bool(request.phone_number)  # Indicate if tracking was enabled
        }
        
        # Add hotel-specific information if hotel filtering was used
        if request.hotel_id and hotel:
            response_data["hotel_filtered"] = True
            response_data["hotel"] = {
                "id": hotel.get("id"),
                "name": hotel.get("name"),
                "slug": hotel.get("slug"),
                "location": hotel.get("location_city"),
                "search_radius_km": hotel.get("search_radius_km", 10)
            }
            response_data["hotel_services_count"] = len(hotel_services)
        else:
            response_data["hotel_filtered"] = False
        
        # Write results to kiosk_results table for real-time push (if phone_number provided)
        if request.phone_number:
            try:
                # Generate timestamp in milliseconds for uniqueness
                timestamp_millis = int(time.time() * 1000)
                
                supabase.table('kiosk_results').insert({
                    "phone_number": request.phone_number,
                    "timestamp_millis": timestamp_millis,
                    "results": response_data,
                    "hotel_id": request.hotel_id,
                    "created_at": datetime.now().isoformat()
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
            "endpoint": "/api/event/by-interests",
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
                "message": "Failed to fetch events from Supabase"
            }
        )

@app.get("/api/logs", response_class=HTMLResponse)
def view_audit_logs():
    """
    View all audit logs in a nice HTML format for debugging
    """
    # Return simple HTML without complex CSS that causes f-string issues
    return HTMLResponse(content=generate_logs_html())

def generate_logs_html():
    """Generate HTML for logs page (separate function to avoid f-string CSS issues)"""
    # Calculate statistics first
    total_logs = len(audit_logs)
    successful_logs = sum(1 for log in audit_logs if log.get("success", False))
    failed_logs = total_logs - successful_logs
    success_rate = round((successful_logs / total_logs * 100) if total_logs > 0 else 0, 1)
    avg_duration = round(sum(log.get("duration_ms", 0) for log in audit_logs) / total_logs if total_logs > 0 else 0, 2)
    
    # Generate log entries HTML
    log_entries_html = ""
    if total_logs > 0:
        for log in reversed(audit_logs):  # Show newest first
            success_class = "success" if log.get("success", False) else "error"
            status_class = "success" if log.get("success", False) else "error"
            
            # Format request body
            request_body_html = ""
            if "request_body" in log and log["request_body"]:
                request_body_html = f"""
                <div class="log-row">
                    <div class="log-label">Request Body:</div>
                    <div class="log-value">
                        <div class="json-box">
                            <pre>{json.dumps(log["request_body"], indent=2)}</pre>
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
                    {request_body_html}
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