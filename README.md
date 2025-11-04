# fastapi-project/README.md

# Spotive - AI-Powered Event Discovery API

Spotive is a conversational AI-powered spot and event finder that helps users discover exciting events through natural phone conversations. No more endless scrolling through apps - just talk and discover!

## Purpose

Spotive solves the frustration of discovering events and activities when you want to go out but don't know what's happening around you. Instead of manually searching through multiple websites and mobile apps, users simply call Spotive and have a natural conversation about their preferences. The AI agent understands what you're looking for and suggests relevant events happening nearby.

**The Problem We Solve:**
- Tired of scrolling through multiple apps to find events?
- Don't know what's happening around you?
- Want personalized suggestions without the hassle?
- Prefer talking over searching?

**Our Solution:**
Spotive is a conversational AI agent that talks to users over phone calls, understands their preferences, remembers them for future interactions, and provides personalized event recommendations from a curated database of upcoming events.

## Project Details

### What Spotive Does

Spotive helps users discover dynamic events and experiences including:
- 🎭 Entertainment venues and shows
- 🎵 Concerts and music events
- ⚽ Sports events
- 🌳 Outdoor activities
- 🍽️ Buffet events and food festivals
- 🙏 Spiritual events
- 🎨 Cultural events
- 👨‍👩‍👧 Kids-friendly events

*Note: Spotive MVP focuses on events and activities, not static locations like regular restaurants.*

### Key Features

- **Conversational Interface**: Talk naturally over phone calls (via Twilio GSM)
- **Personalized Recommendations**: AI-powered suggestions based on your preferences
- **User Memory**: Remembers your preferences for better suggestions next time
- **Smart Event Querying**: Real-time event database search using agentic AI (LangChain)
- **Visual Previews**: Sends event images to your WhatsApp for easy review
- **Seamless Booking**: Shares location and booking links via WhatsApp when you confirm
- **No App Required**: Just call and talk - no need to download or scroll through apps

### Technology Stack

**AI & Conversational Layer:**
- **ElevenLabs**: Conversational AI agent with Text-to-Speech capabilities
- **LangChain**: Agentic AI framework for intelligent event querying
- **Ollama**: Local LLM for development
- **OpenAI API**: Production LLM for enhanced performance

**Communication:**
- **Twilio**: Phone calls (GSM) and WhatsApp messaging
- **Next.js**: ElevenLabs integration frontend

**Backend & Data:**
- **FastAPI**: High-performance API backend (this repository)
- **Supabase**: Event database with curated upcoming events
- **MCP Protocol**: Model Context Protocol for Supabase integration
- **Uvicorn**: ASGI server

**Deployment:**
- **Vercel**: Hosting for both API and Next.js application

### Target Audience

Spotive is perfect for anyone who:
- Wants to go out but has no idea what events are happening around them
- Is tired of scrolling through multiple apps and websites
- Prefers natural conversation over manual searching
- Values personalized recommendations
- Wants to discover new experiences effortlessly

### Project Status

- **Stage**: MVP (Minimum Viable Product)
- **Language**: English
- **Initial Launch Location**: Bangalore, India
- **Team**: AI Development Team

## Project Structure

```
fastapi-project
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── endpoints
│   │   │   └── __init__.py
│   ├── core
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models
│   │   └── __init__.py
│   └── schemas
│       └── __init__.py
├── tests
│   └── __init__.py
├── requirements.txt
└── README.md
```

## Installation

### 1. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy the `env.template` file to create your `.env` file:

```bash
cp env.template .env
```

The template already includes the Supabase credentials, but you can customize other settings.

### 3. Install Ollama (for local development)

Download and install Ollama from [https://ollama.ai](https://ollama.ai), then pull the Gemma3 model:

```bash
ollama pull gemma3
```

### 4. Set Up Supabase Database

1. Go to your Supabase project: https://wopjezlgtborpnhcfvoc.supabase.co
2. Navigate to the SQL Editor
3. Follow the instructions in `SUPABASE_SETUP.md` to create the events table
4. Insert sample data or add your own events

See `SUPABASE_SETUP.md` for detailed database setup instructions.

## Running the Application

Start the FastAPI server with hot reload:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

## API Endpoints

Once running, you can access these endpoints:

### GET Endpoints

- **`GET /`** - Health check and API info
- **`GET /api/random-event`** - Get a random event with conversational AI description
- **`GET /api/event/category/{category}`** - Get an event from a specific category
  - Categories: `concert`, `sports`, `outdoor`, `food`, `spiritual`, `cultural`, `kids`, `entertainment`
- **`GET /api/events/all`** - Get all events (for testing)

### POST Endpoints

- **`POST /api/events/by-preferences`** - Get events filtered by date and user preferences using MCP
  - Request body: `{ "date": "2025-11-15", "preferences": "music, outdoor, family-friendly" }`
  - Returns top 3 ranked results with AI conversational descriptions

### Example Usage

```bash
# Get a random event suggestion
curl http://127.0.0.1:8000/api/random-event

# Get a concert event
curl http://127.0.0.1:8000/api/event/category/concert

# Get all events
curl http://127.0.0.1:8000/api/events/all

# Get events by date and preferences (POST)
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, entertainment, outdoor"}'
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc` 

## License

This project is licensed under the MIT License.