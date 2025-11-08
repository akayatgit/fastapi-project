# Spotive Hotel Kiosk API

**AI-Powered Concierge API for Hotel Kiosk Systems**

Spotive Hotel Kiosk API is the backend service powering interactive hotel concierge kiosks. It provides intelligent event discovery, hotel service recommendations, and guest preference management for touchscreen kiosks deployed in hotel lobbies.

---

## 🎯 Purpose

This API serves standing tablet kiosks in hotels, enabling guests to discover:
- 🎭 **Nearby Events** - Concerts, shows, cultural activities
- 🍽️ **Hotel Services** - Spa, restaurants, bars, room service
- 🚕 **Local Experiences** - Tours, attractions, shopping
- 📱 **WhatsApp Sharing** - Send recommendations directly to guest phones

**The Problem We Solve:**
- Reduce load on hotel concierge desks
- Enhance guest engagement through self-service discovery
- Increase hotel revenue via upselling in-house services
- Provide 24/7 multilingual concierge assistance

**Our Solution:**
A robust API that combines conversational AI, local event data, and hotel-specific services to power voice-enabled kiosk interfaces deployed in hotel lobbies and near elevators.

---

## 🏨 Use Case

### Target Deployment
- **Location**: Hotel lobbies, elevator areas, guest service floors
- **Hardware**: Standing tablet kiosks (12"+ touchscreen)
- **Frontend**: Next.js web application with ElevenLabs voice integration calls this API via webhooks integration *(separate project)*
- **This API**: Backend service providing data, AI logic, and analytics

### Guest Journey
1. Guest approaches kiosk in hotel lobby
2. Interacts via voice or touch: *"What's happening tonight?"*
3. API processes query → returns nearby events + hotel services
4. Guest selects options → sends details to WhatsApp
5. Hotel analytics track engagement and conversions

---

## ✨ Key Features

### For Guests
- **🎤 Voice-Enabled Discovery** - Natural language event search
- **🎨 Personalized Recommendations** - AI learns from guest preferences
- **📍 Location-Aware Results** - Events and attractions near the hotel
- **🏨 In-House Upsells** - Spa, restaurant, bar, tours, cabs
- **📱 WhatsApp Integration** - Send recommendations to phone
- **🌍 Multilingual Support** - Multiple language interfaces

### For Hotels
- **🎨 White-Label Branding** - Custom logo, colors, theme per hotel
- **📊 Analytics Dashboard** - Query volume, top interests, conversions
- **💰 Revenue Opportunities** - Track upsell conversions
- **⚙️ Easy Configuration** - Manage services and branding via API
- **🔒 Privacy-Focused** - No guest accounts required

---

## 🏗️ Architecture

### System Overview
```
Hotel Guest (Kiosk) 
    ↓
Next.js Frontend (Voice + Touch UI)
    ↓
[THIS API] FastAPI + LangChain
    ↓ ↓ ↓
Supabase        ElevenLabs*      Twilio*
(Events +       (Voice AI)       (WhatsApp)
 Hotels +       
 Services)       

* Integrated via frontend
```

### Technology Stack

**Backend (This Repository):**
- **FastAPI** - High-performance Python API framework
- **LangChain** - Agentic AI for intelligent querying
- **Supabase** - PostgreSQL database for events, hotels, user profiles
- **Pydantic** - Request/response validation
- **Uvicorn** - ASGI production server

**AI Layer:**
- **Ollama** (Local dev) - Free LLM for testing
- **OpenAI API** (Production) - GPT-3.5-turbo for Vercel deployment
- **LLM-Powered Features**:
  - Interest → Category mapping
  - Conversational event descriptions
  - Smart search result ranking

**Integrations:**
- **Twilio** - WhatsApp messaging (planned as the last feature)
- **ElevenLabs** - Voice AI (handled by frontend)

**Deployment:**
- **Vercel** - Serverless hosting
- **Supabase** - Cloud PostgreSQL database

---

## 📊 Database Schema

### Core Tables

**1. Events** - Local attractions and activities
```
- id, name, category, description
- location, date, time, price
- image_url, booking_link
- hotel_id (for hotel-specific events)
```

**2. Users** - Guest profiles and preferences
```
- phone_number (unique identifier)
- username, favorite_categories (JSONB)
- total_searches, last_active
```

**3. User Search History** - Track guest interactions
```
- user_id, search_query
- mapped_categories (JSONB)
- search_timestamp, results_count
```

**4. User Preferences** - Manual guest preferences
```
- user_id, preferred_categories
- preferred_locations, time_slots
- price_range (JSONB)
```

**5. Hotels** *(Planned)*
```
- name, location, branding (JSONB)
- logo_url, brand_colors, timezone
```

**6. Hotel Services** *(Planned)*
```
- hotel_id, service_type (spa/restaurant/bar)
- name, description, price_range
- booking_link, available_hours
```

See `SUPABASE_SETUP.md` for complete schema and setup SQL.

---

## 🚀 Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create `.env` file:

```bash
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# LLM Configuration
LLM_PROVIDER=ollama          # Use 'openai' for production
LLM_MODEL=gemma3             # Use 'gpt-3.5-turbo' for OpenAI
OPENAI_API_KEY=sk-...        # Required if LLM_PROVIDER=openai

# Optional
IS_VERCEL=false
IS_PRODUCTION=false
```

### 3. Install Ollama (Local Development)

```bash
# Download from https://ollama.ai
ollama pull gemma3
```

### 4. Set Up Supabase Database

1. Create Supabase project
2. Run SQL from `SUPABASE_SETUP.md`:
   - Events table
   - Users tables (3 tables)
3. Insert sample event data
4. Disable Row Level Security OR add policies

---

## 🏃 Running the API

### Local Development
```bash
uvicorn app.main:app --reload
```

API available at: **http://localhost:8000**

### Interactive Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📡 API Endpoints

### **Core Event Discovery**

#### `POST /api/event/by-interests`
Get events based on user interests with optional profile tracking.

**Request:**
```json
{
  "interests": "comedy, music",
  "phone_number": "+919876543210"  // Optional: for tracking
}
```

**Response:**
```json
{
  "success": true,
  "mapped_categories": ["comedy", "concert"],
  "total_matching_events": 12,
  "events": [
    {
      "suggestion": "Check out this hilarious standup show...",
      "event_details": {
        "id": 1,
        "name": "Comedy Night",
        "category": "comedy",
        "location": "Indiranagar",
        "date": "2025-11-15",
        "time": "20:00",
        "price": "₹500"
      }
    }
  ],
  "personalized": true
}
```

---

### **User Profile Management**

#### `POST /api/users/register`
Register or retrieve guest profile.

**Request:**
```json
{
  "phone_number": "+919876543210",
  "username": "Guest Name"
}
```

#### `GET /api/users/{phone_number}`
Get complete user profile with search history.

**Response:**
```json
{
  "user": {
    "phone_number": "+919876543210",
    "total_searches": 15,
    "favorite_categories": {
      "comedy": 8,
      "concert": 5,
      "outdoor": 2
    },
    "top_3_interests": ["comedy", "concert", "outdoor"]
  },
  "recent_searches": [...]
}
```

#### `PUT /api/users/{phone_number}/preferences`
Update guest preferences manually.

#### `POST /api/users/{phone_number}/discover-events`
Get personalized recommendations based on accumulated preferences.

---

### **Analytics & Monitoring**

#### `GET /api/logs`
View audit logs (HTML dashboard).

#### `GET /api/logs/analytics`
Advanced analytics with filters.

#### `GET /api/logs/export`
Export logs as CSV.

---

### **Utility**

#### `GET /`
API health check and environment info.

---

## 📚 Documentation

| File | Description |
|------|-------------|
| `SUPABASE_SETUP.md` | Complete database schema and SQL setup |
| `USER_PROFILES_API_GUIDE.md` | User profile API documentation with examples |
| `IMPLEMENTATION_SUMMARY.md` | Implementation overview and features |

---

## 🔄 How Preference Accumulation Works

The API automatically learns guest preferences:

```
Guest Search 1: "comedy shows"
→ favorite_categories: {"comedy": 1}

Guest Search 2: "more comedy"
→ favorite_categories: {"comedy": 2}

Guest Search 3: "music concerts"
→ favorite_categories: {"comedy": 2, "concert": 1}

After 10+ searches:
→ favorite_categories: {"comedy": 7, "concert": 2, "outdoor": 1}
→ top_3_interests: ["comedy", "concert", "outdoor"]

Next search: "something fun"
→ System combines "fun" + learned preferences
→ Returns personalized comedy & music events
```

---

## 🚀 Deployment to Vercel

### Environment Variables (Required)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
OPENAI_API_KEY=sk-...        # ⚠️ REQUIRED for Vercel
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
IS_VERCEL=true
IS_PRODUCTION=true
```

### Deploy

**Option A: GitHub**
1. Push to GitHub
2. Import in Vercel dashboard
3. Add environment variables
4. Deploy automatically

**Option B: Vercel CLI**
```bash
vercel --prod
```

### Verify Deployment
```bash
curl https://your-api.vercel.app/
# Check: "llm_available": true
```

---

## 🎨 White-Label Configuration

Each hotel can have custom branding:

```json
{
  "hotel_id": "uuid",
  "name": "Taj Wellington Mews",
  "branding": {
    "logo_url": "https://...",
    "primary_color": "#C4A962",
    "secondary_color": "#1A1A1A"
  },
  "location": {
    "city": "Mumbai",
    "area": "Colaba",
    "radius_km": 10
  }
}
```

*(Hotel management endpoints coming in Phase 2)*

---

## 📱 WhatsApp Integration (Planned)

Send event details to guest phones:

```python
POST /api/send-to-whatsapp
{
  "phone_number": "+919876543210",
  "event_id": "uuid"
}
```

Uses Twilio API to send formatted event details via WhatsApp.

---

## 🔧 Project Structure

```
fastapi-project/
├── app/
│   ├── main.py              # Main API application
│   ├── core/
│   │   └── config.py        # Environment configuration
│   ├── api/                 # API routes (future)
│   ├── models/              # Database models (future)
│   └── schemas/             # Pydantic schemas (future)
├── tests/                   # Unit tests
├── requirements.txt         # Python dependencies
├── vercel.json             # Vercel configuration
├── SUPABASE_SETUP.md       # Database setup guide
├── USER_PROFILES_API_GUIDE.md  # API documentation
└── README.md               # This file
```

---

## 🧪 Testing

### Quick Test Flow

```bash
# 1. Register a guest
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919876543210", "username": "Test Guest"}'

# 2. Search for events (preferences accumulate automatically)
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy shows", "phone_number": "+919876543210"}'

# 3. Check accumulated preferences
curl http://localhost:8000/api/users/+919876543210

# 4. Get personalized recommendations
curl -X POST http://localhost:8000/api/users/+919876543210/discover-events \
  -H "Content-Type: application/json" \
  -d '{"interests": "entertainment"}'
```

---

## 📊 Analytics Features

Track kiosk engagement:
- **Query Volume** - Total searches per day/week
- **Top Interests** - Most searched categories
- **Conversion Rate** - WhatsApp shares vs views
- **Session Duration** - Average interaction time
- **Hotel Performance** - Compare across properties

Access via: `GET /api/logs/analytics`

---

## 🎯 Development Roadmap

### ✅ Phase 1: Core API (Complete)
- [x] Event discovery with LLM mapping
- [x] User profile management
- [x] Automatic preference accumulation
- [x] Search history tracking
- [x] Personalized recommendations
- [x] Analytics logging

### 🔄 Phase 2: Hotel Features (In Progress)
- [ ] Multi-hotel management tables
- [ ] Hotel services API (spa, restaurant, bar)
- [ ] Hotel-specific event filtering
- [ ] WhatsApp integration (Twilio)
- [ ] Hotel analytics dashboard
- [ ] White-label configuration API

### 🔜 Phase 3: Advanced Features
- [ ] Hotel PMS integration
- [ ] Dynamic pricing for services
- [ ] Guest loyalty tracking
- [ ] Multilingual content support
- [ ] A/B testing for recommendations
- [ ] Real-time event updates

---

## 🤝 Integration with Frontend

**Frontend Repository**: *(Separate Next.js project with ElevenLabs voice integration)*

### API Contract
The frontend kiosk application consumes these endpoints:

```javascript
// Discovery
POST /api/event/by-interests
POST /api/users/{phone}/discover-events

// User Management
POST /api/users/register
GET /api/users/{phone}

// Services (Coming Soon)
GET /api/hotels/{hotel_id}/services
POST /api/send-to-whatsapp
```

---

## 🐛 Troubleshooting

### Issue: "User not found"
**Solution**: Run SQL from `SUPABASE_SETUP.md` to create tables

### Issue: Phone validation fails
**Solution**: Use Indian format `+91XXXXXXXXXX` (10 digits after +91)

### Issue: Preferences not accumulating
**Check**:
1. Phone number sent with requests?
2. Supabase tables created?
3. Row Level Security disabled or policies set?

### Issue: LLM not working
**Check**:
- Local: Ollama running? (`ollama list`)
- Vercel: `OPENAI_API_KEY` environment variable set?

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Project Info

- **Stage**: MVP → Hotel Kiosk Pivot
- **Current Focus**: API backend for kiosk deployments
- **Target Market**: Hotels in India (expanding)
- **Team**: AI Development Team

---

## 📞 Support

For issues or questions:
1. Check `USER_PROFILES_API_GUIDE.md` for detailed API docs
2. Check `SUPABASE_SETUP.md` for database setup
3. View logs at `/api/logs` for debugging
4. Test endpoints at `/docs` (Swagger UI)

---

**Built with ❤️ for seamless hotel guest experiences**
