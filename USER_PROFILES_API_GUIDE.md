# User Profiles & Preferences API Guide

Complete guide to using the new User Profiles feature in Spotive API.

---

## 🎯 Overview

The User Profiles feature allows you to:
- ✅ Register users with phone numbers
- ✅ Automatically track search history
- ✅ Accumulate user preferences over time
- ✅ Provide personalized event recommendations
- ✅ Manually set user preferences
- ✅ View detailed user profiles and analytics

---

## 📋 Prerequisites

1. Complete the Supabase database setup (see `SUPABASE_SETUP.md`)
2. Ensure your API is running with Supabase connection
3. Have valid Indian phone numbers for testing (+91XXXXXXXXXX format)

---

## 🔌 API Endpoints

### 1. Register a User

**POST** `/api/users/register`

Register a new user or retrieve an existing user.

**Request Body:**
```json
{
  "phone_number": "+919876543210",
  "username": "Ashok Kumar"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "uuid-here",
    "phone_number": "+919876543210",
    "username": "Ashok Kumar",
    "created_at": "2025-11-08T10:30:00",
    "last_active": "2025-11-08T10:30:00",
    "total_searches": 0,
    "favorite_categories": {},
    "top_3_interests": []
  }
}
```

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "username": "Ashok Kumar"
  }'
```

---

### 2. Get User Profile

**GET** `/api/users/{phone_number}`

Retrieve complete user profile including search history and preferences.

**Path Parameter:**
- `phone_number`: User's phone number (e.g., +919876543210)

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "phone_number": "+919876543210",
    "username": "Ashok Kumar",
    "created_at": "2025-11-08T10:30:00",
    "last_active": "2025-11-08T15:45:00",
    "total_searches": 15,
    "favorite_categories": {
      "comedy": 10,
      "music": 3,
      "outdoor": 2
    },
    "top_3_interests": ["comedy", "music", "outdoor"]
  },
  "preferences": {
    "preferred_categories": ["comedy", "outdoor"],
    "preferred_locations": ["Indiranagar", "Koramangala"],
    "preferred_time_slots": ["evening", "weekend"],
    "price_range": {"min": 0, "max": 1500},
    "avoid_categories": []
  },
  "recent_searches": [
    {
      "query": "standup comedy shows",
      "categories": ["comedy"],
      "timestamp": "2025-11-08T15:45:00",
      "results_count": 5
    },
    {
      "query": "music concerts",
      "categories": ["concert"],
      "timestamp": "2025-11-08T14:30:00",
      "results_count": 8
    }
  ]
}
```

**Example (cURL):**
```bash
curl http://localhost:8000/api/users/+919876543210
```

---

### 3. Update User Preferences

**PUT** `/api/users/{phone_number}/preferences`

Manually update user preferences. All fields are optional.

**Path Parameter:**
- `phone_number`: User's phone number

**Request Body:**
```json
{
  "preferred_categories": ["comedy", "outdoor", "food"],
  "preferred_locations": ["Indiranagar", "Koramangala", "Whitefield"],
  "preferred_time_slots": ["evening", "weekend"],
  "price_range": {"min": 0, "max": 2000},
  "avoid_categories": ["spiritual"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Preferences updated successfully",
  "preferences": {
    "id": "uuid",
    "user_id": "user-uuid",
    "preferred_categories": ["comedy", "outdoor", "food"],
    "preferred_locations": ["Indiranagar", "Koramangala", "Whitefield"],
    "preferred_time_slots": ["evening", "weekend"],
    "price_range": {"min": 0, "max": 2000},
    "avoid_categories": ["spiritual"],
    "updated_at": "2025-11-08T16:00:00"
  }
}
```

**Example (cURL):**
```bash
curl -X PUT http://localhost:8000/api/users/+919876543210/preferences \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_categories": ["comedy", "music"],
    "preferred_locations": ["Indiranagar"],
    "price_range": {"min": 0, "max": 1000}
  }'
```

---

### 4. Discover Events (Personalized)

**POST** `/api/users/{phone_number}/discover-events`

Get personalized event recommendations based on user profile and accumulated preferences.

**Path Parameter:**
- `phone_number`: User's phone number

**Request Body:**
```json
{
  "interests": "comedy"
}
```

**Note:** The `interests` field is **optional**. If omitted, uses user's accumulated preferences only.

**Response:**
```json
{
  "success": true,
  "personalized": true,
  "user_top_categories": ["comedy", "music", "outdoor"],
  "original_interests": "comedy",
  "combined_interests_used": "comedy, comedy, music, outdoor",
  "mapped_categories": ["comedy"],
  "mapping_method": "llm",
  "total_matching_events": 12,
  "returned_events": 5,
  "events": [
    {
      "suggestion": "Check out this hilarious standup comedy show...",
      "event_details": {
        "id": "event-uuid",
        "name": "Comedy Night at BFlat",
        "category": "comedy",
        "location": "Indiranagar",
        "date": "2025-11-15",
        "time": "8:00 PM",
        "price": "₹500",
        "image_url": "https://...",
        "booking_link": "https://..."
      }
    }
  ],
  "source": "Supabase",
  "ai_generated": true
}
```

**Example (cURL):**
```bash
# With interests
curl -X POST http://localhost:8000/api/users/+919876543210/discover-events \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy shows"}'

# Using profile only (no interests)
curl -X POST http://localhost:8000/api/users/+919876543210/discover-events \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### 5. Event Discovery with Optional Tracking (Backward Compatible)

**POST** `/api/event/by-interests`

The original endpoint now supports **optional** phone number tracking.

**Request Body:**
```json
{
  "interests": "comedy, music",
  "phone_number": "+919876543210"
}
```

**Note:** The `phone_number` field is **optional**. If provided:
- User will be automatically created if not exists
- Search will be tracked in history
- Preferences will be accumulated

**Response:**
```json
{
  "success": true,
  "interests": "comedy, music",
  "mapped_categories": ["comedy", "concert"],
  "mapping_method": "llm",
  "total_matching_events": 15,
  "returned_events": 5,
  "events": [...],
  "source": "Supabase",
  "ai_generated": true,
  "personalized": true
}
```

**Example (cURL):**
```bash
# With tracking
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "standup comedy",
    "phone_number": "+919876543210"
  }'

# Without tracking (original behavior)
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "standup comedy"
  }'
```

---

## 🔄 Complete User Journey Example

### Step 1: Register User
```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+919876543210",
    "username": "Rahul"
  }'
```

### Step 2: Make First Search
```bash
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "comedy shows",
    "phone_number": "+919876543210"
  }'
```

**What happens:**
- User's `favorite_categories["comedy"]` increases by 1
- Search is saved in `user_search_history`
- `total_searches` increments
- `last_active` updates

### Step 3: Make More Searches
```bash
# Search 2: Comedy again
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "standup",
    "phone_number": "+919876543210"
  }'

# Search 3: Music
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "live music concerts",
    "phone_number": "+919876543210"
  }'

# Search 4: Outdoor
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "trekking",
    "phone_number": "+919876543210"
  }'
```

### Step 4: Check Accumulated Preferences
```bash
curl http://localhost:8000/api/users/+919876543210
```

**Response shows:**
```json
{
  "favorite_categories": {
    "comedy": 2,
    "concert": 1,
    "outdoor": 1
  },
  "top_3_interests": ["comedy", "concert", "outdoor"]
}
```

### Step 5: Get Personalized Recommendations
```bash
# Now just say "something fun" and it will use accumulated preferences
curl -X POST http://localhost:8000/api/users/+919876543210/discover-events \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "something fun"
  }'
```

The system will combine "something fun" with the user's top categories (comedy, concert, outdoor) for better results!

---

## 📊 How Preferences Accumulate

### Automatic Accumulation Rules:

1. **Every Search** → Category counter +1
   ```
   User searches "comedy" → favorite_categories["comedy"] += 1
   ```

2. **Multiple Categories** → All categories get +1
   ```
   User searches "comedy and music" → 
   favorite_categories["comedy"] += 1
   favorite_categories["concert"] += 1
   ```

3. **Repeated Searches** → Preferences strengthen over time
   ```
   After 10 comedy searches → favorite_categories["comedy"] = 10
   After 2 music searches → favorite_categories["concert"] = 2
   
   Top interests: ["comedy", "concert"]
   ```

### Example Timeline:

| Search # | Query | Categories Mapped | Accumulated Prefs |
|----------|-------|-------------------|-------------------|
| 1 | "comedy" | ["comedy"] | {"comedy": 1} |
| 2 | "standup" | ["comedy"] | {"comedy": 2} |
| 3 | "music concerts" | ["concert"] | {"comedy": 2, "concert": 1} |
| 4 | "comedy shows" | ["comedy"] | {"comedy": 3, "concert": 1} |
| 5 | "trekking" | ["outdoor"] | {"comedy": 3, "concert": 1, "outdoor": 1} |

**Top 3 Interests:** `["comedy", "concert", "outdoor"]`

---

## 🔐 Phone Number Validation

All phone numbers must follow this format:
- **Format:** `+91XXXXXXXXXX`
- **Country Code:** `+91` (India)
- **Digits:** Exactly 10 digits after +91
- **First Digit:** Must be 6-9 (Indian mobile numbers)

**Valid Examples:**
- ✅ `+919876543210`
- ✅ `+918765432109`
- ✅ `+917654321098`

**Invalid Examples:**
- ❌ `9876543210` (missing +91)
- ❌ `+91123456789` (first digit is 1)
- ❌ `+9198765432` (only 8 digits)
- ❌ `+919876543210123` (too many digits)

---

## 🎯 Use Cases

### Use Case 1: First-Time User
```
1. User calls hotline
2. Register: POST /api/users/register
3. Ask interests: "What do you like?"
4. Search: POST /api/event/by-interests (with phone_number)
5. Return events
```

### Use Case 2: Returning User
```
1. User calls again
2. Search: POST /api/users/{phone}/discover-events
3. Send interests OR leave empty to use profile
4. Get personalized results based on history
```

### Use Case 3: User Profile Management
```
1. Admin/User wants to set preferences manually
2. Update: PUT /api/users/{phone}/preferences
3. Set preferred categories, locations, price range
4. Future searches will respect these preferences
```

### Use Case 4: Analytics & Insights
```
1. Get profile: GET /api/users/{phone}
2. View:
   - Total searches
   - Favorite categories
   - Recent search history
   - Top 3 interests
3. Use for marketing/recommendations
```

---

## 🚀 Integration with Voice/WhatsApp

### Voice Integration Example:
```python
# Pseudo-code for voice integration
def handle_voice_call(caller_number):
    # Register/get user
    user = register_user(caller_number, "User")
    
    # Convert speech to text
    user_speech = speech_to_text()
    
    # Get personalized events
    if user.total_searches > 5:
        # Use profile for returning users
        events = discover_events_personalized(caller_number, "")
    else:
        # Ask for interests for new users
        events = get_events_by_interests(user_speech, caller_number)
    
    # Convert events to speech
    text_to_speech(events[0]["suggestion"])
```

### WhatsApp Bot Example:
```python
# Pseudo-code for WhatsApp bot
@whatsapp_bot.message_handler()
def handle_message(message, sender_phone):
    # Auto-register user
    user = register_user(sender_phone, message.sender_name)
    
    # Get personalized events
    events = discover_events_personalized(
        sender_phone, 
        message.text
    )
    
    # Send formatted response
    send_whatsapp_message(sender_phone, format_events(events))
```

---

## 📈 Future Enhancements

The current implementation is designed to support future features:

1. **Time Decay** - Recent searches weigh more
2. **Negative Feedback** - "Not interested" decreases preference
3. **Location-Based Ranking** - Sort by distance to preferred locations
4. **Price Filtering** - Auto-filter by price range
5. **Notifications** - Alert users about new matching events
6. **Social Features** - Friend recommendations
7. **Event Ratings** - Learn from user feedback

---

## 🐛 Troubleshooting

### Error: "User not found"
**Solution:** Register the user first using `/api/users/register`

### Error: "Invalid phone number format"
**Solution:** Use format `+91XXXXXXXXXX` with exactly 10 digits after +91

### Error: "No interests provided and user has no search history"
**Solution:** Either:
- Provide `interests` in the request body, OR
- Make some searches first to build up profile

### Issue: Preferences not accumulating
**Check:**
1. Are you sending `phone_number` with searches?
2. Is phone number in correct format?
3. Check database: `SELECT * FROM users WHERE phone_number = '+91XXX'`
4. Check search history: `SELECT * FROM user_search_history WHERE user_id = 'xxx'`

---

## 🔗 Related Documentation

- **Database Setup:** See `SUPABASE_SETUP.md`
- **Main API Docs:** Check FastAPI auto-docs at `/docs`
- **Analytics Dashboard:** See `/api/logs/analytics`

---

## ✅ Testing Checklist

- [ ] Register a new user
- [ ] Make 3-5 searches with phone_number
- [ ] Check user profile shows accumulated preferences
- [ ] Use personalized discovery endpoint
- [ ] Update preferences manually
- [ ] Verify phone number validation works
- [ ] Test with and without phone_number
- [ ] Check search history is saved
- [ ] Verify backward compatibility (old API still works)

---

## 📞 Support

For issues or questions:
1. Check this guide
2. Check `SUPABASE_SETUP.md`
3. View API documentation at `/docs`
4. Check logs at `/api/logs`

---

**Happy Building! 🎉**

