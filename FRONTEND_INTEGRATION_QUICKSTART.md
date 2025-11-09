# 🚀 Frontend Integration - Quick Start (5 Minutes)

**For Next.js developers: Copy-paste this code to get real-time results working!**

---

## 🎯 TL;DR - How It Works

**Question:** *"How does the kiosk UI get results when ElevenLabs calls the API?"*

**Answer in 3 steps:**

1. **Next.js collects guest's phone number** upfront
   ```typescript
   const phoneNumber = "+919876543210"  // From input field
   ```

2. **Next.js subscribes** to Supabase real-time for that phone_number
   ```typescript
   filter: `phone_number=eq.+919876543210`
   ```

3. **ElevenLabs calls API** with phone_number in body
   ```json
   {"interests": "comedy", "phone_number": "+919876543210"}
   ```

4. **FastAPI generates unique timestamp** and writes results
   ```python
   timestamp = int(time.time() * 1000)  # Current time in milliseconds
   INSERT (phone_number, timestamp_millis, results)
   ```

5. **Next.js receives results** via Supabase real-time broadcast

**Result:** Results appear on screen in real-time! ⚡ (50-150ms)

---

## 📋 **Purpose & Requirements**

### **Purpose of This Feature**

**The Problem:**
In a hotel kiosk system, there are **3 separate components** that need to communicate:
1. **Next.js Frontend** (displays the UI)
2. **ElevenLabs Agent** (handles voice conversation)
3. **FastAPI Backend** (processes event search)

When ElevenLabs calls the FastAPI backend, the Next.js frontend has **no way to know what results were returned**. This creates a disconnect between the voice response and the visual display.

**The Solution:**
Use **Supabase Real-Time** as a messaging bus to push results from FastAPI to Next.js in real-time, synchronized with the voice response. We use **phone_number as the identifier** since we collect it anyway for WhatsApp sharing.

**The Goal:**
- ✅ Guest enters phone number once
- ✅ Guest speaks: "I want comedy shows"
- ✅ Guest hears: AI voice describing comedy events
- ✅ Guest sees: Event cards appearing on screen simultaneously
- ✅ Perfect synchronization between voice and visual

---

### **Why Phone Number Instead of Session ID?**

**Advantages:**
- ✅ Already collecting phone for WhatsApp feature
- ✅ No need to pass session_id through ElevenLabs
- ✅ Simpler ElevenLabs configuration
- ✅ Guest can resume on another device with same phone
- ✅ Can track user history across sessions
- ✅ One identifier for everything

**How Uniqueness is Ensured:**
- Phone number + timestamp in milliseconds = unique identifier
- Example: `+919876543210_1699478912345`
- Multiple searches by same guest = different timestamps
- No collision possible

---

### **Requirements**

#### **Backend Requirements:** ✅ ALREADY DONE
- [x] FastAPI with Supabase integration
- [x] Event discovery endpoint (`/api/event/by-interests`)
- [x] Phone number in request body
- [x] Generate timestamp internally
- [x] Write results to `kiosk_results` table
- [x] Hotel management system
- [x] International phone validation

#### **Database Requirements:** ⏳ YOUR TASK
- [ ] Create `kiosk_results` table in Supabase
- [ ] Enable real-time replication on the table
- [ ] Set up automatic cleanup (optional)

**SQL to run:**
```sql
CREATE TABLE kiosk_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT NOT NULL,
    timestamp_millis BIGINT NOT NULL,
    unique_id TEXT GENERATED ALWAYS AS (phone_number || '_' || timestamp_millis::text) STORED,
    results JSONB NOT NULL,
    hotel_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_kiosk_results_unique ON kiosk_results(phone_number, timestamp_millis);
CREATE INDEX idx_kiosk_results_phone ON kiosk_results(phone_number);
CREATE INDEX idx_kiosk_results_created ON kiosk_results(created_at DESC);

-- CRITICAL: Enable real-time
ALTER TABLE kiosk_results REPLICA IDENTITY FULL;
```

#### **Frontend Requirements:** ⏳ YOUR TASK
- [ ] Next.js application (already exists)
- [ ] Install `@supabase/supabase-js` package
- [ ] Supabase credentials (URL + anon key)
- [ ] ElevenLabs SDK integration (already exists)
- [ ] Phone number input field
- [ ] Implement real-time subscription

#### **ElevenLabs Configuration:** ⏳ YOUR TASK
- [ ] Define custom variables (hotel_id, api_url)
- [ ] Configure webhook URL
- [ ] Update agent to extract phone from conversation
- [ ] Test webhook calls

---

## 🔄 **Complete Workflow Explanation**

### **Scenario: Guest Searches for Comedy Shows**

Let's walk through a **real example** step-by-step:

---

#### **STEP 1: Guest Provides Phone Number** (Next.js)

```typescript
// Guest enters phone number at kiosk
const [phoneNumber, setPhoneNumber] = useState('');

// Input field
<input 
  type="tel"
  value={phoneNumber}
  onChange={(e) => setPhoneNumber(e.target.value)}
  placeholder="+919876543210"
/>

// After entering: phoneNumber = "+919876543210"
```

**What's happening:**
- Guest enters phone number for WhatsApp sharing
- Next.js stores it in state
- Will use this to subscribe to real-time results

---

#### **STEP 2: Subscribe to Real-Time** (Next.js)

```typescript
// Subscribe to Supabase for this phone number
useEffect(() => {
  if (!phoneNumber) return;  // Wait for phone number
  
  const channel = supabase
    .channel(`phone:${phoneNumber}`)
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'kiosk_results',
      filter: `phone_number=eq.${phoneNumber}`  // ⭐ Filter by phone!
    }, (payload) => {
      console.log('✅ Results received!');
      setEvents(payload.new.results.events);
      setIsListening(false);
    })
    .subscribe();
  
  return () => supabase.removeChannel(channel);
}, [phoneNumber]);

// Status: Subscribed to +919876543210
```

**What's happening:**
- Next.js subscribes to Supabase real-time
- Filter: Only show results for THIS phone number
- Ready to receive results for this guest

---

#### **STEP 3: Start Voice Conversation** (Next.js → ElevenLabs)

```typescript
// Guest taps "Speak" button
const startConversation = async () => {
  if (!phoneNumber) {
    alert('Please enter your phone number first');
    return;
  }
  
  setIsListening(true);
  
  // Start ElevenLabs - MUCH SIMPLER NOW!
  await window.elevenlabs.startConversation({
    agentId: process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID,
    variables: {
      phone_number: phoneNumber,      // ⭐ Just pass phone number
      hotel_id: params.hotelId,
      api_url: process.env.NEXT_PUBLIC_API_URL
    }
  });
};
```

**What's happening:**
- Guest clicks speak button
- Phone number validation
- Pass phone_number to ElevenLabs (simpler than session_id!)
- ElevenLabs starts listening

---

#### **STEP 4: Voice Conversation** (Guest ↔ ElevenLabs)

```
ElevenLabs Agent: "Hello! What would you like to do today?"
Guest: "I want to see comedy shows tonight"
ElevenLabs Agent: "Great! Let me find comedy shows for you..."
```

**What's happening:**
- ElevenLabs listens to guest's voice
- Converts speech to text: "comedy shows"
- Extracts interests: `extracted_interests = "comedy shows"`
- Has phone_number from variables
- Prepares to call webhook

---

#### **STEP 5: Webhook Call** (ElevenLabs → FastAPI)

```
ElevenLabs calls webhook:

POST https://fastapi-project-tau.vercel.app/api/event/by-interests

Headers:
  Content-Type: application/json

Body:
{
  "interests": "comedy shows",
  "phone_number": "+919876543210",  ⭐ From variables
  "hotel_id": "marriott-bangalore"
}
```

**What's happening:**
- ElevenLabs uses stored variables to build request
- Phone number included in request body
- No session_id needed! Simpler!
- Calls FastAPI

---

#### **STEP 6: Event Processing** (FastAPI)

```python
# FastAPI receives request
def get_event_by_interests(request: InterestsRequest):
    # Extract from request body
    phone_number = request.phone_number  # "+919876543210"
    interests = request.interests        # "comedy shows"
    hotel_id = request.hotel_id         # "marriott-bangalore"
    
    # 1. Map interests to categories
    categories = ["comedy"]
    
    # 2. Query events
    events = query_events(categories)
    
    # 3. Get hotel services
    hotel_services = get_hotel_services(hotel_id, categories)
    
    # 4. Generate AI descriptions
    results = generate_descriptions(events)
    
    # 5. ⭐ Generate unique timestamp
    timestamp_millis = int(time.time() * 1000)
    # Result: 1699478912345 (milliseconds since epoch)
    
    # 6. ⭐ Write to kiosk_results with phone + timestamp
    supabase.table('kiosk_results').insert({
        "phone_number": "+919876543210",
        "timestamp_millis": 1699478912345,
        "results": {...},
        "hotel_id": "marriott-bangalore"
    }).execute()
    
    # Unique ID auto-generated: "+919876543210_1699478912345"
    
    # 7. Return to ElevenLabs
    return results
```

**What's happening:**
- FastAPI processes the search
- Generates current timestamp in milliseconds
- Writes to Supabase with phone_number + timestamp
- Database auto-generates unique_id
- Returns results to ElevenLabs

---

#### **STEP 7: Database Broadcast** (Supabase)

```
Supabase detects:
  New INSERT on kiosk_results table
  phone_number = "+919876543210"
  timestamp_millis = 1699478912345

Supabase real-time broadcasts:
  Event: INSERT
  Table: kiosk_results
  Data: {
    phone_number: "+919876543210",
    timestamp_millis: 1699478912345,
    results: { events: [...] }
  }

Broadcast to ALL subscribers via WebSocket

Latency: 50-150ms ⚡
```

**What's happening:**
- Supabase detects new row inserted
- Broadcasts INSERT event to all connected clients
- Next.js subscription receives the broadcast
- Only shows it if phone_number matches

---

#### **STEP 8: Results Received** (Next.js)

```typescript
// Subscription receives broadcast
.on('postgres_changes', {
  filter: `phone_number=eq.${phoneNumber}`  // Filter matches!
}, (payload) => {
  console.log('✅ Results received!');
  
  const results = payload.new.results;
  setEvents(results.events);  // Update React state
  
  // React re-renders → Cards appear on screen! 🎉
});
```

**What's happening:**
- Next.js subscription receives the broadcast
- Checks filter: phone_number matches ✅
- Extracts events from results
- Updates React state
- UI re-renders with event cards

---

#### **STEP 9: Synchronized Experience** (Guest View)

```
Guest Experience:

👂 HEARS (from speakers):
"I found 3 great comedy shows for you! 
First, there's a standup comedy night at BFlat Bar..."

👀 SEES (on screen):
┌─────────────────────────────┐
│ 🎭 Comedy Night at BFlat    │
│ Tonight at 8 PM | ₹500      │
│ 📍 2.3km away               │
│ [📱 Send to WhatsApp]       │
└─────────────────────────────┘

┌─────────────────────────────┐
│ 🏨 Alto Vino Bar (Hotel)   │
│ Happy Hour Comedy | ₹800    │
│ 📍 Here at the hotel        │
│ [📱 Send to WhatsApp]       │
└─────────────────────────────┘

Results appear WHILE agent is speaking! ✅
Perfect synchronization! ✅
```

**What's happening:**
- Voice and visual perfectly synchronized
- Guest can read while listening
- Hotel services prominently displayed
- Phone number already entered for easy WhatsApp share

---

## 🎯 **Why This Architecture?**

### **Advantages of Phone Number Approach:**

✅ **Simpler ElevenLabs Config** - No session_id to pass through  
✅ **One Identifier** - Phone number used for everything  
✅ **Natural Flow** - Already collecting phone for WhatsApp  
✅ **Multi-Device** - Guest can continue on another kiosk  
✅ **User Tracking** - Link searches to same guest  
✅ **No Extra Variables** - Just phone_number, hotel_id  

### **Challenges We Solved:**

**Challenge 1:** ElevenLabs server-side webhook
- ❌ Can't directly return results to browser
- ✅ Solution: Write to database, broadcast via real-time

**Challenge 2:** Multiple concurrent guests
- ❌ How to avoid showing Guest A's results to Guest B?
- ✅ Solution: Each guest has unique phone number, filtered subscriptions

**Challenge 3:** Multiple searches by same guest
- ❌ How to distinguish search 1 vs search 2?
- ✅ Solution: Add timestamp in milliseconds (unique per search)

**Challenge 4:** Cost and complexity
- ❌ Redis/WebSocket servers add cost and infrastructure
- ✅ Solution: Use Supabase real-time (already have it, $0 cost)

---

## 📊 **Data Flow Summary**

```
Component          Action                              Data
─────────────────────────────────────────────────────────────
Next.js         → Collect phone number             → "+919876543210"
                  ↓
Next.js         → Subscribe to Supabase            → filter: phone_number=eq.+919876543210
                  ↓
Next.js         → Pass to ElevenLabs               → variables: {phone_number: "+91..."}
                  ↓
ElevenLabs      → Store variable                   → conversation.phone_number = "+91..."
                  ↓
Guest           → Speaks                           → "comedy shows"
                  ↓
ElevenLabs      → Extract interests                → interests = "comedy shows"
                  ↓
ElevenLabs      → Call FastAPI                     → POST with phone_number in body
                  ↓
FastAPI         → Generate timestamp               → timestamp = 1699478912345
                  ↓
FastAPI         → Process search                   → Find events
                  ↓
FastAPI         → Write to Supabase                → INSERT (phone, timestamp, results)
                  ↓
Supabase        → Broadcast INSERT                 → Real-time WebSocket
                  ↓
Next.js         → Receive (if filter matches)      → phone_number=eq.+919876543210 ✅
                  ↓
Next.js         → Update UI                        → setEvents(...)
                  ↓
Screen          → Display cards                    → Guest sees results! 🎉

Total Time: ~2-3 seconds (mostly LLM processing)
Real-time broadcast: 50-150ms ⚡
```

---

## ⚡ Quick Setup

### **1. Install Supabase** (30 seconds)

```bash
npm install @supabase/supabase-js
```

---

### **2. Add Environment Variables** (30 seconds)

```bash
# .env.local
NEXT_PUBLIC_SUPABASE_URL=https://wopjezlgtborpnhcfvoc.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=https://fastapi-project-tau.vercel.app
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your-agent-id
```

---

### **3. Create Supabase Client** (30 seconds)

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

---

### **4. Complete Kiosk Component** (3 minutes)

```typescript
// app/kiosk/[hotelId]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export default function KioskPage({ params }: { params: { hotelId: string } }) {
  // State
  const [phoneNumber, setPhoneNumber] = useState('');
  const [events, setEvents] = useState<any[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [phoneEntered, setPhoneEntered] = useState(false);

  // ⭐ Subscribe to real-time results for this phone number
  useEffect(() => {
    if (!phoneNumber || !phoneEntered) return;
    
    console.log('📡 Subscribing to phone:', phoneNumber);
    
    const channel = supabase
      .channel(`phone:${phoneNumber}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'kiosk_results',
        filter: `phone_number=eq.${phoneNumber}`,  // ⭐ Filter by phone!
      }, (payload) => {
        console.log('✅ Results received!', payload);
        
        const results = payload.new.results;
        if (results && results.events) {
          setEvents(results.events);
          setIsListening(false);
        }
      })
      .subscribe((status) => {
        console.log('📡 Subscription status:', status);
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [phoneNumber, phoneEntered]);

  // Start voice conversation
  const startConversation = async () => {
    if (!phoneNumber) {
      alert('Please enter your phone number first');
      return;
    }
    
    setIsListening(true);
    setEvents([]);

    try {
      // @ts-ignore
      await window.elevenlabs.startConversation({
        agentId: process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID,
        
        // ⭐ MUCH SIMPLER - Just pass phone_number!
        variables: {
          phone_number: phoneNumber,
          hotel_id: params.hotelId,
          api_url: process.env.NEXT_PUBLIC_API_URL
        }
      });
    } catch (error) {
      console.error('Failed to start conversation:', error);
      setIsListening(false);
    }
  };

  // Handle phone number submission
  const handlePhoneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!phoneNumber.startsWith('+')) {
      alert('Phone number must include country code (e.g., +91...)');
      return;
    }
    
    if (phoneNumber.length < 10) {
      alert('Please enter a valid phone number');
      return;
    }
    
    setPhoneEntered(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8 text-center">
        <h1 className="text-4xl font-bold mb-2">
          Welcome to Marriott Bangalore
        </h1>
        <p className="text-gray-600">
          Discover events and activities nearby
        </p>
      </div>

      {/* Phone Number Input */}
      {!phoneEntered ? (
        <div className="max-w-md mx-auto bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-bold mb-4">Get Started</h2>
          <p className="text-gray-600 mb-6">
            Enter your phone number to receive event details on WhatsApp
          </p>
          
          <form onSubmit={handlePhoneSubmit}>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+919876543210"
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg text-lg mb-4"
              required
            />
            
            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-lg text-lg font-bold hover:bg-blue-700"
            >
              Continue →
            </button>
          </form>
          
          <p className="text-sm text-gray-500 mt-4">
            We'll use this to send event details to your WhatsApp
          </p>
        </div>
      ) : (
        <>
          {/* Voice Button */}
          <div className="text-center mb-8">
            <button
              onClick={startConversation}
              disabled={isListening}
              className={`
                px-12 py-6 rounded-full text-2xl font-bold
                ${isListening 
                  ? 'bg-red-500 animate-pulse cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700 active:scale-95'
                }
                text-white transition-all shadow-lg
              `}
            >
              {isListening ? '🎤 Listening...' : '🗣️ Tap to Speak'}
            </button>
            
            {isListening && (
              <p className="mt-4 text-gray-600 animate-pulse">
                Searching for events...
              </p>
            )}
          </div>

          {/* Debug Info */}
          <div className="max-w-7xl mx-auto mb-4 p-4 bg-gray-100 rounded text-sm">
            <p><strong>Phone:</strong> {phoneNumber}</p>
            <p><strong>Hotel:</strong> {params.hotelId}</p>
            <p><strong>Status:</strong> {isListening ? 'Listening' : 'Ready'}</p>
            <p><strong>Events:</strong> {events.length}</p>
          </div>

          {/* Events Grid */}
          {events.length > 0 && (
            <div className="max-w-7xl mx-auto">
              <h2 className="text-2xl font-bold mb-6">
                Found {events.length} results for you:
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {events.map((event, index) => (
                  <EventCard 
                    key={index} 
                    event={event}
                    phoneNumber={phoneNumber}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Event Card Component
function EventCard({ event, phoneNumber }: { event: any, phoneNumber: string }) {
  const { suggestion, event_details } = event;

  const sendToWhatsApp = async () => {
    // TODO: Implement WhatsApp send
    alert(`Will send ${event_details.name} to ${phoneNumber}`);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
      {/* Image */}
      {event_details.image_url && (
        <img
          src={event_details.image_url}
          alt={event_details.name}
          className="w-full h-48 object-cover"
        />
      )}

      {/* Content */}
      <div className="p-6">
        {/* Badges */}
        {event_details.is_hotel_service && (
          <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-sm font-semibold rounded-full mb-2">
            🏨 Hotel Service
          </span>
        )}

        {event_details.distance_km !== undefined && event_details.distance_km !== null && (
          <span className="inline-block px-3 py-1 bg-green-100 text-green-800 text-sm font-semibold rounded-full mb-2 ml-2">
            📍 {event_details.distance_km === 0 ? 'Here' : `${event_details.distance_km}km away`}
          </span>
        )}

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          {event_details.name}
        </h3>

        {/* AI Suggestion */}
        <p className="text-gray-700 mb-4 leading-relaxed">
          {suggestion}
        </p>

        {/* Details */}
        <div className="space-y-2 text-sm text-gray-600 mb-4">
          <p>📍 {event_details.location}</p>
          <p>📅 {event_details.date}</p>
          <p>🕐 {event_details.time}</p>
          <p className="font-semibold text-gray-900">💰 {event_details.price}</p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {event_details.booking_link && (
            <a
              href={event_details.booking_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700 transition"
            >
              Book Now
            </a>
          )}
          
          <button
            onClick={sendToWhatsApp}
            className="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition"
          >
            📱 Send to WhatsApp
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## ⚙️ **ElevenLabs Agent Configuration (SIMPLIFIED!)**

### **Step-by-Step ElevenLabs Setup:**

**1. Go to ElevenLabs Dashboard → Your Agent → Configure**

**2. Add Custom Variables:**
```
Variable 1:
  Name: phone_number
  Type: string
  Required: Yes
  Description: Guest's phone number from kiosk input

Variable 2:
  Name: hotel_id
  Type: string
  Required: Yes
  Description: Hotel identifier (slug or UUID)

Variable 3:
  Name: api_url
  Type: string
  Required: Yes
  Default: https://fastapi-project-tau.vercel.app
  Description: Backend API base URL
```

**3. Configure Webhook:**
```
Tool Name: search_events
Description: Search for events based on guest interests

HTTP Method: POST
URL: {{api_url}}/api/event/by-interests

Headers:
  Content-Type: application/json

Request Body:
{
  "interests": "{{extracted_interests}}",
  "phone_number": "{{phone_number}}",
  "hotel_id": "{{hotel_id}}"
}

Response Handling:
  The agent should read the "events" array and tell the guest about them.
```

**4. Update Agent Prompt:**
```
You are a helpful hotel concierge assistant.

You have access to these variables:
- phone_number: Guest's phone number (for sending details)
- hotel_id: Current hotel location
- api_url: Backend API URL

When a guest tells you what they're interested in:
1. Extract their interests (e.g., "comedy shows", "spa", "food")
2. Call the search_events tool with the extracted interests and phone_number
3. The tool will return matching events and hotel services
4. Tell the guest about the results in a friendly, conversational way

Note: The phone_number is already provided - don't ask the guest for it again.
```

**5. Test in ElevenLabs:**
```
In the test panel:
1. Set test values:
   - phone_number: "+919876543210"
   - hotel_id: "marriott-bangalore"
   - api_url: "https://fastapi-project-tau.vercel.app"

2. Type: "I want comedy shows"

3. Verify webhook is called correctly

4. Check response contains events
```

---

## 🧪 Testing

### **Test 1: Backend**

```bash
# Test with phone number
curl -X POST "https://fastapi-project-tau.vercel.app/api/event/by-interests" \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "comedy",
    "phone_number": "+919876543210",
    "hotel_id": "marriott-bangalore"
  }'

# Check Supabase table - should see row with your phone number
```

### **Test 2: Frontend Subscription**

```typescript
// Test in browser console
const testPhone = '+919876543210';

// Subscribe
const channel = supabase
  .channel(`test-${testPhone}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'kiosk_results',
    filter: `phone_number=eq.${testPhone}`
  }, (payload) => {
    console.log('✅ Received:', payload);
  })
  .subscribe();

// Then call API with this phone number
// You should see the console log!
```

### **Test 3: End-to-End**

1. Open kiosk page
2. Enter phone number: +919876543210
3. Click "Continue"
4. Click "Tap to Speak"
5. Say: "I want comedy shows"
6. Watch results appear in real-time! ⚡

---

## 🔍 **How Phone Number Works**

### **Uniqueness Strategy:**

```python
# FastAPI generates unique identifier:
phone_number = "+919876543210"
timestamp_millis = 1699478912345  # Current time in milliseconds

# Unique ID (auto-generated in database):
unique_id = "+919876543210_1699478912345"

# Multiple searches by same guest:
Search 1: "+919876543210_1699478912345"
Search 2: "+919876543210_1699478912567"  ← Different timestamp!
Search 3: "+919876543210_1699478913012"
```

**Why This Works:**
- Millisecond precision ensures uniqueness
- Same guest can do multiple searches
- Each search gets its own results
- Frontend receives all results for their phone number

---

### **Frontend Receives Multiple Results:**

If guest does multiple searches, frontend receives all of them:

```typescript
.on('postgres_changes', {
  filter: `phone_number=eq.${phoneNumber}`
}, (payload) => {
  // Receives EVERY insert for this phone number
  const newResults = payload.new.results;
  
  // Option 1: Replace with latest (recommended)
  setEvents(newResults.events);
  
  // Option 2: Accumulate (show history)
  setEvents(prev => [...newResults.events, ...prev]);
});
```

**Recommended:** Replace with latest results (Option 1) for clean UX

---

## 🐛 Troubleshooting

### **Issue 1: "No results appearing"**

**Check:**
```typescript
// 1. Phone number entered?
console.log('Phone:', phoneNumber);  // Should not be empty

// 2. Subscription active?
.subscribe((status) => {
  console.log('Status:', status);  // Should be "SUBSCRIBED"
});

// 3. Results received?
.on('postgres_changes', {}, (payload) => {
  console.log('Payload:', payload);  // Should see data
});
```

**Most Common:** Real-time not enabled
**Solution:** Run `ALTER TABLE kiosk_results REPLICA IDENTITY FULL;`

---

### **Issue 2: "Receiving wrong results"**

**Check Filter:**
```typescript
// ❌ WRONG
filter: `phone_number=${phoneNumber}`

// ✅ CORRECT (note the 'eq.')
filter: `phone_number=eq.${phoneNumber}`
```

---

### **Issue 3: "Phone number validation failed"**

**Solution:** Phone number format
```typescript
// ✅ Valid formats:
+919876543210   (India)
+14155552671    (USA)
+442071234567   (UK)
+96362260992    (Syria)

// ❌ Invalid:
9876543210      (missing +)
+91 987 654     (spaces not allowed)
```

**API accepts all international formats!**

---

### **Issue 4: "Multiple searches showing all results"**

**Solution:** Take only latest
```typescript
.on('postgres_changes', {}, (payload) => {
  // Only show latest search results
  setEvents(payload.new.results.events);  // Replaces previous
  
  // NOT this (accumulates):
  // setEvents(prev => [...payload.new.results.events, ...prev]);
});
```

---

## 🎯 **Why This is Better Than Session ID**

| Aspect | Session ID Approach | Phone Number Approach |
|--------|---------------------|----------------------|
| **Complexity** | Must pass through ElevenLabs | Already in request body |
| **ElevenLabs Config** | 3 variables | 3 variables (but simpler) |
| **Guest Experience** | Transparent | Natural (already entering phone) |
| **Multi-Search** | New session_id each time | Same phone, different timestamp |
| **WhatsApp Integration** | Need phone anyway | Already have it! |
| **User Tracking** | Anonymous sessions | Linked to guest |
| **Resume on Another Kiosk** | Cannot resume | Can resume with same phone |
| **Debugging** | Random UUIDs | Real phone numbers (easier) |

**Winner:** Phone Number Approach ✅

---

## 📊 **Architecture Comparison**

### **Old (Session ID):**
```
Next.js → Generate session_id → Pass to ElevenLabs → 
Use in webhook → FastAPI gets session_id → Write with session_id
```

### **New (Phone Number):** ⭐ SIMPLER
```
Next.js → Collect phone_number → Pass to ElevenLabs → 
Use in webhook → FastAPI generates timestamp → Write with phone + timestamp
```

**Benefit:** One less moving part, simpler to debug!

---

## ✅ **Frontend Team Checklist**

### **Setup (One-time):**
- [ ] Install `@supabase/supabase-js`
- [ ] Add environment variables (.env.local)
- [ ] Create `lib/supabase.ts` with Supabase client
- [ ] Configure ElevenLabs agent with phone_number variable
- [ ] Configure webhook URL in ElevenLabs

### **Implementation:**
- [ ] Add phone number input field
- [ ] Validate phone number format (+country code)
- [ ] Store phone number in React state
- [ ] Subscribe to Supabase real-time with phone_number filter
- [ ] Pass phone_number to ElevenLabs in `variables` object
- [ ] Display events when subscription receives data
- [ ] Unsubscribe on component unmount

### **Testing:**
- [ ] Enter phone number
- [ ] Check subscription status: "SUBSCRIBED"
- [ ] Start conversation
- [ ] Speak interests
- [ ] Verify results appear on screen
- [ ] Check Supabase table has rows
- [ ] Test multiple searches with same phone
- [ ] Test with different phone numbers

### **ElevenLabs Configuration:**
- [ ] Add custom variables (phone_number, hotel_id, api_url)
- [ ] Set webhook URL (no session_id in URL now!)
- [ ] Add phone_number to request body
- [ ] Update agent prompt
- [ ] Test in ElevenLabs dashboard

---

## 🎯 **Critical Code Snippets**

### **1. Collect phone number:**
```typescript
const [phoneNumber, setPhoneNumber] = useState('');

<input 
  type="tel"
  value={phoneNumber}
  onChange={(e) => setPhoneNumber(e.target.value)}
  placeholder="+919876543210"
/>
```

### **2. Pass to ElevenLabs:**
```typescript
await window.elevenlabs.startConversation({
  agentId: 'your-agent-id',
  variables: {
    phone_number: phoneNumber,  // ⭐ Just phone number!
    hotel_id: params.hotelId
  }
});
```

### **3. Subscribe to real-time:**
```typescript
supabase
  .channel(`phone:${phoneNumber}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'kiosk_results',
    filter: `phone_number=eq.${phoneNumber}`  // ⭐ Filter by phone!
  }, (payload) => {
    setEvents(payload.new.results.events);
  })
  .subscribe();
```

---

## 📞 **Key Differences from Session ID Approach**

### **What Changed:**

**Removed:**
- ❌ Session ID generation in Next.js
- ❌ Passing session_id through ElevenLabs
- ❌ session_id in webhook URL query parameter

**Added:**
- ✅ Phone number input field (needed for WhatsApp anyway)
- ✅ Phone number validation
- ✅ Timestamp generation in FastAPI (automatic)

**Simplified:**
- ✅ ElevenLabs configuration (no session_id variable)
- ✅ Frontend code (phone already collected)
- ✅ Debugging (phone numbers are readable)

---

## 🎉 **Summary**

**What Frontend Team Needs:**
1. ✅ Collect phone number from guest (input field)
2. ✅ Subscribe to Supabase with phone_number filter
3. ✅ Pass phone_number to ElevenLabs (simpler!)
4. ✅ Display results when received
5. ✅ Use phone_number for WhatsApp sharing

**Total Setup Time:** 5-10 minutes  
**Complexity:** Simpler than session_id approach!  
**Cost:** $0  
**Performance:** Same (50-150ms) ⚡  

---

## 📞 **Support & Documentation**

**For detailed technical docs:**
- See: `REALTIME_SESSION_GUIDE.md`

**For backend API reference:**
- See: `README.md`
- Or visit: https://fastapi-project-tau.vercel.app/docs

**For database setup:**
- See: `SUPABASE_SETUP.md`

**Need help?**
- Check browser console for errors
- Check Supabase logs
- Verify ElevenLabs webhook is called
- Test backend independently with curl

---

**Happy Coding! 🚀**

**This approach is simpler and better! Phone number = universal identifier! 📱**
