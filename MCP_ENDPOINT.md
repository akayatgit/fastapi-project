# MCP-Based Event Filtering Endpoint

## Overview

The `/api/events/by-preferences` endpoint uses **Model Context Protocol (MCP)** to intelligently filter and rank events based on user preferences and date.

## Endpoint Details

**Method**: `POST`  
**URL**: `/api/events/by-preferences`  
**Content-Type**: `application/json`

## How It Works

### Step-by-Step Process

1. **Fetch Events by Date**
   - Queries Supabase for all events on the specified date
   - Returns 404 if no events found for that date

2. **MCP Filtering**
   - Sends event list and user preferences to LLM
   - LLM analyzes each event against preferences
   - Returns ranked list of matching event IDs

3. **Smart Matching**
   - Uses intelligent preference matching:
     - "family" or "kids" → matches kids-friendly events
     - "adventure" → matches outdoor/sports events
     - "cultural" or "traditional" → matches cultural/spiritual events
     - "music" or "entertainment" → matches concerts/entertainment
     - "free" or "cheap" → filters by price
     - And more contextual matching...

4. **Generate AI Descriptions**
   - Creates conversational descriptions for top 3 results
   - Each description is a natural 20-word chat message
   - Perfect for TTS (Text-to-Speech) with ElevenLabs

## Request Format

```json
{
  "date": "2025-11-15",
  "preferences": "music, outdoor, family-friendly"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Event date in YYYY-MM-DD format |
| `preferences` | string | Yes | Comma-separated user preferences |

### Example Preferences

**Event Types:**
- `music`, `concert`, `sports`, `outdoor`, `food`, `spiritual`, `cultural`, `kids`, `entertainment`

**Interests:**
- `adventure`, `relaxation`, `social`, `learning`, `traditional`, `modern`

**Activity Level:**
- `active`, `relaxing`, `family-friendly`, `solo`, `group`

**Budget:**
- `free`, `cheap`, `moderate`, `premium`, `budget-friendly`

**Other:**
- `evening`, `morning`, `weekend`, `indoor`, `outdoor`, `central bangalore`, `north bangalore`

## Response Format

```json
{
  "success": true,
  "date": "2025-11-15",
  "preferences": "music, entertainment, outdoor",
  "total_events_on_date": 5,
  "matched_events": 3,
  "top_results": [
    {
      "rank": 1,
      "suggestion": "You've got to check out the Sunburn Music Festival at Palace Grounds this weekend! It's an incredible EDM fest with international DJs that'll keep you dancing outdoors all night long.",
      "event_details": {
        "id": 1,
        "name": "Sunburn Music Festival",
        "category": "concert",
        "description": "Electronic dance music festival with international DJs",
        "location": "Palace Grounds, Bangalore",
        "date": "2025-11-15",
        "time": "18:00",
        "price": "₹2000 - ₹5000",
        "image_url": "https://example.com/sunburn.jpg",
        "booking_link": "https://bookmyshow.com/sunburn"
      }
    },
    {
      "rank": 2,
      "suggestion": "..."
    },
    {
      "rank": 3,
      "suggestion": "..."
    }
  ],
  "all_matched_ids": ["1", "3", "5"],
  "source": "Supabase + MCP Filtering"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the request succeeded |
| `date` | string | The queried date |
| `preferences` | string | The user preferences used |
| `total_events_on_date` | integer | Total events available on that date |
| `matched_events` | integer | Number of events matching preferences |
| `top_results` | array | Top 3 ranked events with AI descriptions |
| `top_results[].rank` | integer | Ranking position (1-3) |
| `top_results[].suggestion` | string | Conversational AI description (20 words) |
| `top_results[].event_details` | object | Full event information |
| `all_matched_ids` | array | All event IDs that matched (ranked) |
| `source` | string | Data source indicator |

## Usage Examples

### Basic Request

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, entertainment"}'
```

### Family Event Request

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-09", "preferences": "kids, family-friendly, outdoor"}'
```

### Budget-Conscious Request

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-12", "preferences": "free, spiritual, cultural"}'
```

### Adventure Seeker Request

```bash
curl -X POST http://127.0.0.1:8000/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-11", "preferences": "adventure, outdoor, active, morning"}'
```

### Python Example

```python
import requests

url = "http://127.0.0.1:8000/api/events/by-preferences"
payload = {
    "date": "2025-11-15",
    "preferences": "music, outdoor, evening"
}

response = requests.post(url, json=payload)
data = response.json()

if data["success"]:
    print(f"Found {data['matched_events']} matching events!")
    for result in data["top_results"]:
        print(f"\nRank {result['rank']}: {result['event_details']['name']}")
        print(f"AI Suggestion: {result['suggestion']}")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function getEventsByPreferences() {
  try {
    const response = await axios.post(
      'http://127.0.0.1:8000/api/events/by-preferences',
      {
        date: '2025-11-15',
        preferences: 'music, entertainment, outdoor'
      }
    );
    
    const data = response.data;
    console.log(`Found ${data.matched_events} matching events!`);
    
    data.top_results.forEach(result => {
      console.log(`\nRank ${result.rank}: ${result.event_details.name}`);
      console.log(`Suggestion: ${result.suggestion}`);
    });
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

getEventsByPreferences();
```

## Integration with ElevenLabs

### Use Case: Phone Conversation

When a user calls Spotive and asks for events:

1. **Extract conversation context**:
   - Date: "this weekend" → convert to date
   - Preferences: User mentions "music" and "outdoor"

2. **Call the API**:
```javascript
const response = await fetch('/api/events/by-preferences', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    date: '2025-11-15',
    preferences: 'music, outdoor'
  })
});

const data = await response.json();
```

3. **Send to ElevenLabs TTS**:
```javascript
// Get the top suggestion
const topEvent = data.top_results[0];

// Send to ElevenLabs for voice
await elevenLabs.textToSpeech({
  text: topEvent.suggestion,
  voice: 'spotive-agent'
});

// Also send image to WhatsApp
await twilio.sendWhatsApp({
  to: userPhoneNumber,
  mediaUrl: topEvent.event_details.image_url
});
```

4. **If user confirms**:
```javascript
// Send booking link via WhatsApp
await twilio.sendWhatsApp({
  to: userPhoneNumber,
  body: `Here's the booking link: ${topEvent.event_details.booking_link}`
});
```

## Error Handling

### No Events Found

```json
{
  "success": false,
  "message": "No events found for date: 2025-11-20",
  "date": "2025-11-20",
  "preferences": "music, entertainment"
}
```

**HTTP Status**: `404 Not Found`

### Server Error

```json
{
  "success": false,
  "error": "Database connection failed",
  "message": "Failed to fetch and filter events",
  "date": "2025-11-15",
  "preferences": "music, entertainment"
}
```

**HTTP Status**: `500 Internal Server Error`

## Performance Considerations

- **Top 3 Only**: AI descriptions are only generated for top 3 results to save processing time
- **Fallback**: If MCP filtering fails, all events are returned
- **Caching**: Consider caching LLM results for popular preference combinations
- **Timeout**: LLM calls have a default timeout to prevent hanging requests

## Tips for Best Results

1. **Be Specific**: `"music, outdoor, evening"` is better than just `"fun"`
2. **Use Multiple Preferences**: The more context, the better the matching
3. **Natural Language**: You can use phrases like `"family-friendly"`, `"budget-friendly"`
4. **Combine Types**: Mix event types with context: `"cultural, evening, free"`
5. **Location**: Include location preferences: `"central bangalore"`, `"near airport"`

## Future Enhancements

- [ ] Support date ranges instead of single date
- [ ] Store user preference history in database
- [ ] Learn from user's past confirmations
- [ ] Support location-based filtering (distance from user)
- [ ] Add price range filtering (min/max)
- [ ] Multi-language support
- [ ] Real-time event availability checking

