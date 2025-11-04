# Spotive API - Changelog

## Latest Updates

### ✨ New Feature: MCP-Based Event Filtering (November 2025)

Added intelligent event filtering using Model Context Protocol (MCP) that allows users to find events based on date and natural language preferences.

#### What's New

**New Endpoint: `POST /api/events/by-preferences`**

This endpoint combines:
- Supabase database queries
- AI-powered preference matching
- Conversational descriptions

**Features:**
- 🎯 Smart preference matching (e.g., "family" → kids events, "adventure" → outdoor)
- 📊 Ranked results (top 3 with full AI descriptions)
- 💬 20-word conversational responses perfect for TTS
- 🔍 Context-aware filtering (budget, time, activity level, etc.)

#### Technical Implementation

**Components Added:**
1. `EventPreferencesRequest` - Pydantic model for request validation
2. `mcp_filter_prompt` - LangChain prompt for intelligent filtering
3. `get_event_by_date_prefs()` - Main endpoint handler

**How It Works:**
1. Queries Supabase for events on specified date
2. Sends events + preferences to LLM via MCP
3. LLM returns ranked event IDs
4. Generates conversational descriptions for top 3
5. Returns structured response with rankings

**Libraries Updated:**
- Added `pydantic` models for type safety
- Added `json` for MCP response parsing
- Added `typing` for better type hints
- Added `requests` for testing

#### Documentation

**New Files:**
- `MCP_ENDPOINT.md` - Complete endpoint documentation
- `test_mcp_endpoint.py` - Test script with examples
- Updated `README.md` - Added POST endpoint section
- Updated `QUICKSTART.md` - Added MCP feature guide

#### Example Usage

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-11-15",
    "preferences": "music, outdoor, family-friendly"
  }'
```

#### Response Format

```json
{
  "success": true,
  "date": "2025-11-15",
  "preferences": "music, outdoor, family-friendly",
  "total_events_on_date": 5,
  "matched_events": 3,
  "top_results": [
    {
      "rank": 1,
      "suggestion": "You've got to check out Sunburn...",
      "event_details": { ... }
    }
  ],
  "source": "Supabase + MCP Filtering"
}
```

---

## Previous Updates

### 🔗 Supabase Integration (November 2025)

**Added:**
- Supabase client configuration
- Environment variable management
- Database connection in `main.py`
- Configuration in `app/core/config.py`

**Files:**
- `SUPABASE_SETUP.md` - Database schema guide
- `env.template` - Environment template
- `.gitignore` - Protect sensitive data

**Updated Endpoints:**
- `GET /api/random-event` - Now fetches from Supabase
- `GET /api/event/category/{category}` - Category filtering
- `GET /api/events/all` - Get all events

### 🤖 LLM Integration (November 2025)

**Added:**
- LangChain integration
- Ollama local LLM support
- OpenAI API support (for production)
- Conversational 20-word responses

**Features:**
- Natural language event descriptions
- Phone-call friendly responses
- TTS-optimized output

### 📝 Initial Setup (November 2025)

**Created:**
- FastAPI application structure
- Basic project organization
- README documentation
- Project structure

---

## API Endpoints Summary

### Current Endpoints (v0.1.0 MVP)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API health check |
| GET | `/api/random-event` | Random event with AI description |
| GET | `/api/event/category/{category}` | Events by category |
| GET | `/api/events/all` | All events (testing) |
| POST | `/api/events/by-preferences` | **NEW** - MCP-based filtering |

### Upcoming Features

- [ ] User preference memory/storage
- [ ] Date range queries
- [ ] Location-based filtering (distance)
- [ ] Price range filtering
- [ ] Multi-language support
- [ ] WhatsApp integration endpoints
- [ ] Twilio integration endpoints
- [ ] User history tracking

---

## Tech Stack

**Backend:**
- FastAPI (API framework)
- Uvicorn (ASGI server)
- Supabase (Database)
- Python 3.7+

**AI/LLM:**
- LangChain (Agentic AI)
- Ollama (Local development)
- OpenAI API (Production)
- MCP (Model Context Protocol)

**Integrations (Planned):**
- ElevenLabs (Voice AI)
- Twilio (Phone + WhatsApp)
- Next.js (Frontend)

**Deployment:**
- Vercel (Hosting)

---

## Migration Notes

### From Generic Template → Spotive

The project has evolved from a generic FastAPI template to a specialized event discovery system:

**Changed:**
- Project name: "FastAPI Project" → "Spotive"
- Focus: Generic API → Event discovery
- Data source: None → Supabase
- AI: None → LangChain + Ollama/OpenAI
- Response style: JSON → Conversational

**Maintained:**
- Project structure
- FastAPI framework
- Configuration management
- Testing structure

---

## Breaking Changes

None yet (v0.1.0 MVP)

---

## Contributors

- AI Development Team

---

## License

MIT License

