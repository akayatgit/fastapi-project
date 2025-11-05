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

@app.post("/api/event/by-interests")
def get_event_by_interests(request: InterestsRequest, background_tasks: BackgroundTasks, req: Request):
    """
    Get events based on user interests. The LLM maps interests to categories and queries matching events.
    
    Request body:
    - interests: Comma-separated interests (e.g., "music, outdoor, adventure")
    
    The system will:
    1. Use AI to map interests to event categories
    2. Query events matching those categories
    3. Return a random event with conversational description
    """
    start_time = datetime.now()
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
            # Log to Supabase (async)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            background_tasks.add_task(log_to_supabase, {
                "timestamp": datetime.now().isoformat(),
                "endpoint": "/api/event/by-interests",
                "interests": request.interests,
                "mapped_categories": json.dumps(categories),
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
        
        # Log to Supabase (async) - SUCCESS CASE
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/event/by-interests",
            "interests": request.interests,
            "mapped_categories": json.dumps(categories),
            "total_matching_events": len(events),
            "selected_event_id": event.get("id"),
            "selected_event_name": event.get("name"),
            "selected_event_category": event.get("category"),
            "success": True,
            "error_message": None,
            "response_time_ms": response_time,
            "client_ip": req.client.host if req.client else "unknown",
            "user_agent": req.headers.get("user-agent", "unknown")
        })
        
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
        # Log to Supabase (async) - ERROR CASE
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        background_tasks.add_task(log_to_supabase, {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/api/event/by-interests",
            "interests": request.interests,
            "mapped_categories": None,
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
            setTimeout(function() { location.reload(); }, 5000);
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