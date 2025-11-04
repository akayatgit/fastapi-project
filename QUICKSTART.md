# Spotive API - Quick Start Guide

## 🚀 What's Been Set Up

Your Spotive API is now connected to Supabase! Here's what's ready:

✅ FastAPI application configured  
✅ Supabase integration with your project  
✅ LangChain + Ollama for conversational AI responses  
✅ Three API endpoints ready to use  
✅ Configuration management with environment variables  

## 📋 Next Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI & Uvicorn (API framework)
- Supabase client (database)
- LangChain & Ollama (AI/LLM)
- python-dotenv (environment variables)

### Step 2: Install Ollama

1. Download from: https://ollama.ai
2. Install on your system
3. Pull the Gemma3 model:

```bash
ollama pull gemma3
```

### Step 3: Set Up Supabase Database

Go to your Supabase project and create the `events` table:

**🔗 Supabase Project URL**: https://wopjezlgtborpnhcfvoc.supabase.co

1. Open Supabase Dashboard
2. Go to SQL Editor
3. Copy and run the SQL from `SUPABASE_SETUP.md`
4. Insert the sample events data

**Full instructions**: See `SUPABASE_SETUP.md`

### Step 4: Create .env File

```bash
# On Windows
copy env.template .env

# On Mac/Linux
cp env.template .env
```

The credentials are already set in the template!

### Step 5: Run the API

```bash
uvicorn app.main:app --reload
```

Visit: http://127.0.0.1:8000

## 🧪 Test the API

### Option 1: Browser

Open your browser and go to:
- http://127.0.0.1:8000/api/random-event

### Option 2: Swagger Docs

- http://127.0.0.1:8000/docs

Try the endpoints interactively!

### Option 3: Command Line

```bash
# Random event
curl http://127.0.0.1:8000/api/random-event

# Specific category
curl http://127.0.0.1:8000/api/event/category/concert

# All events
curl http://127.0.0.1:8000/api/events/all

# Events by date and preferences (POST)
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, outdoor, family-friendly"}'
```

## 🎯 How It Works

1. **User calls API** → `/api/random-event`
2. **API fetches from Supabase** → Gets real event data
3. **LLM generates response** → Creates a 3-line conversational description
4. **Returns JSON** → Contains both the AI suggestion and event details

### Example Response

```json
{
  "success": true,
  "suggestion": "Oh man, you gotta check out the Sunburn Music Festival at Palace Grounds! It's gonna be absolutely epic with some of the best international DJs spinning electronic dance music all night. It's on November 15th at 6 PM, tickets are between 2000 to 5000 rupees!",
  "event_details": {
    "id": 1,
    "name": "Sunburn Music Festival",
    "category": "concert",
    "location": "Palace Grounds, Bangalore",
    "date": "2025-11-15",
    "time": "18:00",
    "price": "₹2000 - ₹5000",
    "image_url": "https://example.com/sunburn.jpg",
    "booking_link": "https://bookmyshow.com/sunburn"
  },
  "source": "Supabase"
}
```

## 📱 Integration with ElevenLabs

The `suggestion` field is perfect for ElevenLabs TTS! Just:
1. Call the API from your Next.js app
2. Extract the `suggestion` text
3. Send it to ElevenLabs for voice conversion
4. Play over Twilio phone call

The `event_details` contain:
- `image_url` → Send to WhatsApp via Twilio
- `booking_link` → Send to WhatsApp when user confirms

## 🐛 Troubleshooting

**Problem**: `Import "supabase" could not be resolved`  
**Solution**: Run `pip install -r requirements.txt`

**Problem**: `No events found in database`  
**Solution**: Go to Supabase and insert events (see SUPABASE_SETUP.md)

**Problem**: LLM not responding  
**Solution**: Make sure Ollama is running and gemma3 is pulled

**Problem**: Connection to Supabase fails  
**Solution**: Check your internet connection and verify the credentials in .env

## 🆕 Advanced Feature: MCP-Based Filtering

The API now includes an intelligent filtering endpoint using **Model Context Protocol (MCP)**:

**Endpoint**: `POST /api/events/by-preferences`

### What It Does

1. Takes a **date** and **user preferences** (comma-separated)
2. Fetches all events from Supabase for that date
3. Uses **AI to intelligently filter and rank** events based on preferences
4. Returns **top 3 results** with conversational descriptions

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, outdoor, evening"}'
```

### Smart Matching

The AI understands context:
- "family" → matches kids-friendly events
- "adventure" → matches outdoor/sports
- "cultural" → matches cultural/spiritual events
- "free" or "cheap" → filters by price
- And much more!

See **MCP_ENDPOINT.md** for detailed documentation.

## 📚 Documentation

- **README.md** - Full project documentation
- **SUPABASE_SETUP.md** - Database schema and setup
- **MCP_ENDPOINT.md** - MCP filtering endpoint guide (NEW!)
- **env.template** - Environment variable template

## 🎉 You're Ready!

Your Spotive API is configured and ready to connect with ElevenLabs! Happy coding! 🚀

