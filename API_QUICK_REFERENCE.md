# Spotive API - Quick Reference

## 🚀 Start the API

```bash
uvicorn app.main:app --reload
```

Visit: http://127.0.0.1:8000

---

## 📡 Endpoints

### 1. Random Event
**GET** `/api/random-event`

Returns a random event from Supabase with AI description.

```bash
curl http://127.0.0.1:8000/api/random-event
```

---

### 2. Event by Category
**GET** `/api/event/category/{category}`

Get event from specific category: `concert`, `sports`, `outdoor`, `food`, `spiritual`, `cultural`, `kids`, `entertainment`

```bash
curl http://127.0.0.1:8000/api/event/category/concert
```

---

### 3. All Events
**GET** `/api/events/all`

Get all events (for testing).

```bash
curl http://127.0.0.1:8000/api/events/all
```

---

### 4. 🆕 Events by Date & Preferences (MCP)
**POST** `/api/events/by-preferences`

Intelligent filtering using AI.

**Request:**
```json
{
  "date": "2025-11-15",
  "preferences": "music, outdoor, family-friendly"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, outdoor"}'
```

**Response:**
```json
{
  "success": true,
  "date": "2025-11-15",
  "preferences": "music, outdoor",
  "total_events_on_date": 5,
  "matched_events": 3,
  "top_results": [
    {
      "rank": 1,
      "suggestion": "You've got to check out...",
      "event_details": { ... }
    }
  ]
}
```

---

## 🧪 Testing

### Quick Test
```bash
# Health check
curl http://127.0.0.1:8000/

# Random event
curl http://127.0.0.1:8000/api/random-event
```

### Run Test Script
```bash
python test_mcp_endpoint.py
```

### Interactive Docs
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## 🎯 Common Preferences

**Event Types:**
`music`, `concert`, `sports`, `outdoor`, `food`, `spiritual`, `cultural`, `kids`, `entertainment`

**Interests:**
`adventure`, `relaxation`, `traditional`, `modern`, `social`, `learning`

**Budget:**
`free`, `cheap`, `budget-friendly`, `moderate`, `premium`

**Time:**
`morning`, `evening`, `weekend`, `weekday`

**Other:**
`family-friendly`, `indoor`, `central bangalore`, `active`, `relaxing`

---

## 💡 Example Combinations

```bash
# Family outing
{"date": "2025-11-09", "preferences": "kids, family-friendly, fun"}

# Adventure seeker
{"date": "2025-11-11", "preferences": "adventure, outdoor, active, morning"}

# Budget conscious
{"date": "2025-11-12", "preferences": "free, cultural, spiritual"}

# Music lover
{"date": "2025-11-15", "preferences": "music, entertainment, evening"}

# Food enthusiast
{"date": "2025-11-08", "preferences": "food, buffet, outdoor"}
```

---

## 🔧 Environment Variables

Located in `.env` (copy from `env.template`):

```bash
# Supabase
SUPABASE_URL=https://wopjezlgtborpnhcfvoc.supabase.co
SUPABASE_KEY=your-key-here

# LLM
LLM_PROVIDER=ollama  # or openai
LLM_MODEL=gemma3
# OPENAI_API_KEY=your-key-here
```

---

## 🗄️ Database

**Table:** `events`

**Required Columns:**
- `id` (bigint/uuid)
- `name` (text)
- `category` (text)
- `description` (text)
- `location` (text)
- `date` (text/date)
- `time` (text)
- `price` (text)
- `image_url` (text, optional)
- `booking_link` (text, optional)

See `SUPABASE_SETUP.md` for SQL.

---

## 📚 Full Documentation

- **README.md** - Project overview
- **QUICKSTART.md** - Getting started
- **MCP_ENDPOINT.md** - MCP filtering details
- **SUPABASE_SETUP.md** - Database setup
- **CHANGELOG.md** - Version history

---

## 🐛 Troubleshooting

**API not starting?**
- Check if port 8000 is available
- Install dependencies: `pip install -r requirements.txt`

**No events found?**
- Add events to Supabase (see SUPABASE_SETUP.md)
- Check database connection

**LLM not responding?**
- Start Ollama: `ollama serve`
- Pull model: `ollama pull gemma3`

**Import errors?**
- Reinstall: `pip install -r requirements.txt --force-reinstall`

---

## 📞 Integration Flow

```
User calls via Twilio
    ↓
ElevenLabs Agent processes voice
    ↓
Next.js app calls Spotive API
    ↓
POST /api/events/by-preferences
    ↓
Returns AI suggestion + event details
    ↓
ElevenLabs TTS speaks suggestion
    ↓
Twilio sends image to WhatsApp
    ↓
User confirms
    ↓
Send booking link via WhatsApp
```

---

## ✅ Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Ollama installed and running
- [ ] Gemma3 model pulled (`ollama pull gemma3`)
- [ ] Supabase database created
- [ ] Events table populated
- [ ] `.env` file created
- [ ] API started (`uvicorn app.main:app --reload`)
- [ ] Tested endpoints

---

Made with ❤️ for Spotive

