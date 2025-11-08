# 🚀 Frontend Integration - Quick Start (5 Minutes)

**For Next.js developers: Copy-paste this code to get real-time results working!**

---

## 🎯 TL;DR - How It Works

**Question:** *"How does the kiosk UI get results when ElevenLabs calls the API?"*

**Answer in 3 steps:**

1. **Next.js generates `session_id`** and passes it to ElevenLabs when starting conversation
   ```typescript
   variables: { session_id: "abc-123" }
   ```

2. **ElevenLabs uses it in webhook** to call FastAPI
   ```
   POST /api/event/by-interests?session_id=abc-123
   ```

3. **Next.js subscribes** to Supabase real-time for that session_id
   ```typescript
   filter: `session_id=eq.abc-123`
   ```

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
Use **Supabase Real-Time** as a messaging bus to push results from FastAPI to Next.js in real-time, synchronized with the voice response.

**The Goal:**
- ✅ Guest speaks: "I want comedy shows"
- ✅ Guest hears: AI voice describing comedy events
- ✅ Guest sees: Event cards appearing on screen simultaneously
- ✅ Perfect synchronization between voice and visual

---

### **Requirements**

#### **Backend Requirements:** ✅ ALREADY DONE
- [x] FastAPI with Supabase integration
- [x] Event discovery endpoint (`/api/event/by-interests`)
- [x] Support for `session_id` query parameter
- [x] Write results to `kiosk_results` table
- [x] Hotel management system
- [x] Hotel services integration

#### **Database Requirements:** ⏳ YOUR TASK
- [ ] Create `kiosk_results` table in Supabase
- [ ] Enable real-time replication on the table
- [ ] Set up automatic cleanup (optional)

**SQL to run:**
```sql
CREATE TABLE kiosk_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_kiosk_results_session ON kiosk_results(session_id);

-- CRITICAL: Enable real-time
ALTER TABLE kiosk_results REPLICA IDENTITY FULL;
```

#### **Frontend Requirements:** ⏳ YOUR TASK
- [ ] Next.js application (already exists)
- [ ] Install `@supabase/supabase-js` package
- [ ] Supabase credentials (URL + anon key)
- [ ] ElevenLabs SDK integration (already exists)
- [ ] Implement session management
- [ ] Implement real-time subscription

#### **ElevenLabs Configuration:** ⏳ YOUR TASK
- [ ] Define custom variables (session_id, hotel_id)
- [ ] Configure webhook URL with variables
- [ ] Update agent to use variables
- [ ] Test webhook calls

---

## 🔄 **Complete Workflow Explanation**

### **Scenario: Guest Searches for Comedy Shows**

Let's walk through a **real example** step-by-step:

---

#### **STEP 1: Kiosk Initialization** (Next.js)

```typescript
// When kiosk page loads
const sessionId = crypto.randomUUID();
// Result: "f47ac10b-58cc-4372-a567-0e02b2c3d479"

// Subscribe to Supabase real-time
supabase.channel(`session:${sessionId}`)
  .on('postgres_changes', {
    filter: `session_id=eq.${sessionId}`
  }, (payload) => {
    // This will be called when results arrive
    setEvents(payload.new.results.events);
  })
  .subscribe();

// Status: Waiting for results...
```

**What's happening:**
- Unique session ID generated (like a "mailbox address")
- Kiosk subscribes to its own "mailbox" in Supabase
- Ready to receive results

---

#### **STEP 2: Guest Interaction Starts** (Next.js → ElevenLabs)

```typescript
// Guest taps "Speak" button
startConversation();

// Code inside:
await elevenlabs.startConversation({
  agentId: 'your-agent-id',
  variables: {
    session_id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",  // ⭐ Passed here!
    hotel_id: "marriott-bangalore",
    api_url: "https://fastapi-project-tau.vercel.app"
  }
});
```

**What's happening:**
- Guest clicks button
- Next.js starts ElevenLabs conversation
- **Passes session_id as a variable** (like giving ElevenLabs a "delivery address")
- ElevenLabs stores these variables for the conversation

---

#### **STEP 3: Voice Conversation** (Guest ↔ ElevenLabs)

```
ElevenLabs Agent: "Hello! What would you like to do today?"
Guest: "I want to see comedy shows tonight"
ElevenLabs Agent: "Great! Let me find comedy shows for you..."
```

**What's happening:**
- ElevenLabs listens to guest's voice
- Converts speech to text: "comedy shows"
- Extracts interests: `extracted_interests = "comedy shows"`
- Prepares to call webhook

---

#### **STEP 4: Webhook Call** (ElevenLabs → FastAPI)

```
ElevenLabs builds webhook URL using stored variables:

Template: 
{{api_url}}/api/event/by-interests?session_id={{session_id}}

Replaces variables:
https://fastapi-project-tau.vercel.app/api/event/by-interests?session_id=f47ac10b-58cc-4372-a567-0e02b2c3d479

Makes HTTP POST:
POST https://fastapi-project-tau.vercel.app/api/event/by-interests?session_id=f47ac10b-58cc-4372-a567-0e02b2c3d479

Body:
{
  "interests": "comedy shows",
  "hotel_id": "marriott-bangalore"
}
```

**What's happening:**
- ElevenLabs uses the variables to build the URL
- Session ID included as query parameter
- Calls FastAPI with guest's interests

---

#### **STEP 5: Event Processing** (FastAPI)

```python
# FastAPI receives request
def get_event_by_interests(
    request: InterestsRequest,  # interests="comedy shows"
    session_id: str = "f47ac10b-58cc-4372-a567-0e02b2c3d479"  # From query param
):
    # 1. Map "comedy shows" → ["comedy"] category
    categories = ["comedy"]
    
    # 2. Query events from database
    events = supabase.table('events').select("*").eq('category', 'comedy').execute()
    
    # 3. Get hotel services (spa, restaurant, bar)
    hotel_services = get_hotel_services_as_events(hotel_id, categories)
    
    # 4. Combine and sort (hotel services first, then by distance)
    all_results = hotel_services + nearby_events
    
    # 5. Generate AI descriptions
    for event in all_results:
        description = llm.generate(event)
    
    # 6. Prepare response
    response = {
        "success": true,
        "events": all_results,
        "hotel_services_count": 2,
        ...
    }
    
    # 7. ⭐ Write to kiosk_results table with session_id
    supabase.table('kiosk_results').insert({
        "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "results": response
    }).execute()
    
    # 8. Return to ElevenLabs
    return response
```

**What's happening:**
- FastAPI processes the search
- Finds comedy events
- Gets hotel comedy services (if any)
- Generates conversational descriptions
- **Writes results to Supabase with session_id** ← Critical!
- Returns results to ElevenLabs

---

#### **STEP 6: Database Broadcast** (Supabase)

```
Supabase detects:
  New INSERT on kiosk_results table
  session_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

Supabase real-time broadcasts:
  Event: INSERT
  Table: kiosk_results
  Data: {
    session_id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    results: { events: [...] }
  }

Broadcast to ALL subscribers via WebSocket

Latency: 50-150ms ⚡
```

**What's happening:**
- Supabase detects new row inserted
- Broadcasts INSERT event to all connected clients
- Next.js subscription receives the broadcast
- Only shows it if session_id matches

---

#### **STEP 7: Results Received** (Next.js)

```typescript
// Subscription receives broadcast
.on('postgres_changes', {
  filter: `session_id=eq.${sessionId}`  // Filter matches!
}, (payload) => {
  console.log('✅ Results received!');
  
  const results = payload.new.results;
  // results = {
  //   events: [
  //     { name: "Comedy Night", distance_km: 2.3, ... },
  //     { name: "Standup Show", distance_km: 5.1, ... }
  //   ]
  // }
  
  setEvents(results.events);  // Update React state
  
  // React re-renders → Cards appear on screen! 🎉
});
```

**What's happening:**
- Next.js subscription receives the broadcast
- Checks filter: session_id matches ✅
- Extracts events from results
- Updates React state
- UI re-renders with event cards

---

#### **STEP 8: Synchronized Experience** (Guest View)

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
│ [📱 Send to Phone]          │
└─────────────────────────────┘

┌─────────────────────────────┐
│ 🏨 Alto Vino Bar (Hotel)   │
│ Happy Hour Comedy | ₹800    │
│ 📍 Here at the hotel        │
│ [📱 Send to Phone]          │
└─────────────────────────────┘

Results appear WHILE agent is speaking! ✅
Perfect synchronization! ✅
```

**What's happening:**
- Voice and visual perfectly synchronized
- Guest can read while listening
- Hotel services prominently displayed
- Distance information helps decision-making

---

## 🎯 **Why This Architecture?**

### **Challenges We Solved:**

**Challenge 1:** ElevenLabs server-side webhook
- ❌ Can't directly return results to browser
- ✅ Solution: Write to database, broadcast via real-time

**Challenge 2:** Multiple concurrent kiosks
- ❌ How to avoid showing Kiosk A's results on Kiosk B?
- ✅ Solution: Unique session_id per kiosk, filtered subscriptions

**Challenge 3:** Real-time updates
- ❌ Polling is slow and wastes resources
- ✅ Solution: Supabase real-time WebSocket (push-based)

**Challenge 4:** Cost and complexity
- ❌ Redis/WebSocket servers add cost and infrastructure
- ✅ Solution: Use Supabase real-time (already have it, $0 cost)

---

## 📊 **Data Flow Summary**

```
Component          Action                              Data
─────────────────────────────────────────────────────────────
Next.js         → Generate session_id               → "abc-123"
                  ↓
Next.js         → Pass to ElevenLabs                → variables: {session_id: "abc-123"}
                  ↓
ElevenLabs      → Store variable                    → conversation.session_id = "abc-123"
                  ↓
Guest           → Speaks                            → "comedy shows"
                  ↓
ElevenLabs      → Extract interests                 → interests = "comedy shows"
                  ↓
ElevenLabs      → Build webhook URL                 → ?session_id=abc-123
                  ↓
ElevenLabs      → Call FastAPI                      → POST with session_id
                  ↓
FastAPI         → Process search                    → Find events
                  ↓
FastAPI         → Write to Supabase                 → INSERT (session_id, results)
                  ↓
Supabase        → Broadcast INSERT                  → Real-time WebSocket
                  ↓
Next.js         → Receive (if filter matches)       → session_id=eq.abc-123 ✅
                  ↓
Next.js         → Update UI                         → setEvents(...)
                  ↓
Screen          → Display cards                     → Guest sees results! 🎉

Total Time: ~2-3 seconds (mostly LLM processing)
Real-time broadcast: 50-150ms ⚡
```

---

## 🎯 **Key Benefits**

### **For Guests:**
✅ Voice + Visual synchronized experience  
✅ Can read details while listening  
✅ Quick response time (< 3 seconds)  
✅ Clear, organized display  
✅ Hotel services highlighted  

### **For Hotels:**
✅ Modern, tech-forward image  
✅ Upsell services naturally  
✅ Reduced concierge desk load  
✅ Better guest satisfaction  
✅ Trackable engagement metrics  

### **For Developers:**
✅ Zero-cost solution (no Redis)  
✅ Simple architecture  
✅ Easy to debug  
✅ Scales to 100+ kiosks  
✅ Production-ready  

---

## 🏗️ **System Requirements**

### **1. Supabase Account** ✅
- Project URL: `https://wopjezlgtborpnhcfvoc.supabase.co`
- Anon key: Available in dashboard
- Real-time enabled: Free tier includes it
- **Status:** Already have it!

### **2. FastAPI Backend** ✅
- Deployed to: Vercel (https://fastapi-project-tau.vercel.app)
- Modified endpoint with session_id support
- **Status:** Already implemented!

### **3. Next.js Frontend** ⏳
- React 18+ with hooks support
- Client-side components ('use client')
- Environment variables support
- **Status:** Needs integration code

### **4. ElevenLabs Agent** ⏳
- Agent created and configured
- Conversational AI enabled
- Webhook support
- Custom variables support
- **Status:** Needs configuration

### **5. Network Requirements**
- Stable internet connection for kiosk
- WebSocket support (for real-time)
- HTTPS for secure connections
- **Status:** Standard requirements

---

## 🔍 **Technical Architecture**

### **Components:**

**1. Next.js Kiosk (Frontend)**
- **Role:** Display UI, manage session, show results
- **Technology:** React, TypeScript, Supabase client
- **Responsibilities:**
  - Generate unique session_id
  - Subscribe to Supabase real-time
  - Pass session_id to ElevenLabs
  - Display event cards
  - Handle user interactions

**2. ElevenLabs Agent (Voice Layer)**
- **Role:** Voice conversation, interest extraction
- **Technology:** ElevenLabs Conversational AI
- **Responsibilities:**
  - Listen to guest speech
  - Extract interests from conversation
  - Store session variables
  - Call FastAPI webhook
  - Speak results to guest

**3. FastAPI Backend (Processing)**
- **Role:** Event search, AI processing, data management
- **Technology:** Python, FastAPI, LangChain
- **Responsibilities:**
  - Map interests to categories
  - Query events from database
  - Get hotel services
  - Generate AI descriptions
  - Write results to Supabase

**4. Supabase (Data & Messaging)**
- **Role:** Database + Real-time messaging bus
- **Technology:** PostgreSQL + Real-time WebSocket
- **Responsibilities:**
  - Store events, hotels, services
  - Store temporary results
  - Broadcast INSERT events
  - Manage subscriptions

---

## 📈 **Workflow Timing Breakdown**

```
Action                          Component       Time
──────────────────────────────────────────────────────────
Generate session_id            Next.js         < 1ms
Subscribe to real-time         Next.js         50-100ms
Pass to ElevenLabs            Next.js         < 1ms
Guest speaks                   Guest           2-5s
Speech recognition             ElevenLabs      200-500ms
Extract interests              ElevenLabs      100-300ms
Call webhook                   ElevenLabs      100-200ms
Map interests to categories    FastAPI         500-1000ms (LLM)
Query events                   FastAPI         50-100ms
Get hotel services             FastAPI         50-100ms
Generate descriptions          FastAPI         1000-2000ms (LLM)
Write to kiosk_results        FastAPI         50-100ms
Broadcast to subscribers       Supabase        50-150ms ⚡
Receive in Next.js            Next.js         < 10ms
Update React state            Next.js         < 10ms
Render cards                   Next.js         < 50ms
──────────────────────────────────────────────────────────
TOTAL (after guest speaks):                    ~2-4 seconds
Real-time broadcast:                           50-150ms ⚡
```

**Key insight:** Most time is LLM processing. The real-time part is **instant!**

---

## 🎯 **Why Session ID is Critical**

### **Without session_id:**
```
Problem:
- Kiosk 1 guest searches "comedy"
- Kiosk 2 guest searches "spa"
- Both kiosks receive BOTH results ❌
- Kiosk 1 shows spa results (wrong!)
- Kiosk 2 shows comedy results (wrong!)
- Complete chaos! 🔥
```

### **With session_id:**
```
Solution:
- Kiosk 1: session_id = "aaa-111", searches "comedy"
  → Results written with session_id="aaa-111"
  → Only Kiosk 1 receives (filter matches) ✅
  
- Kiosk 2: session_id = "bbb-222", searches "spa"
  → Results written with session_id="bbb-222"
  → Only Kiosk 2 receives (filter matches) ✅

Perfect isolation! Each kiosk independent! 🎯
```

---

## 💡 **Design Decisions Explained**

### **Why Supabase Real-Time?**
- ✅ Already using Supabase for data
- ✅ Zero additional cost
- ✅ No extra infrastructure
- ✅ Built-in WebSocket
- ✅ Automatic reconnection
- ✅ Free tier sufficient for 100 kiosks

### **Why Not Polling?**
- ❌ Slow (500-1000ms delay)
- ❌ High server load
- ❌ Battery drain on tablets
- ❌ Wastes bandwidth
- ❌ Poor user experience

### **Why Not WebSocket Server?**
- ❌ Extra $5/month cost
- ❌ Additional infrastructure to manage
- ❌ Deployment complexity
- ❌ Overkill for MVP
- ✅ Good for scale later (100+ kiosks)

### **Why session_id as Query Parameter?**
- ✅ Easy to pass from ElevenLabs
- ✅ Visible in logs (debugging)
- ✅ No body parsing needed
- ✅ Standard HTTP practice
- ✅ Works with ElevenLabs webhook system

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

### **4. Copy This Complete Kiosk Component** (2 minutes)

```typescript
// app/kiosk/[hotelId]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export default function KioskPage({ params }: { params: { hotelId: string } }) {
  // Session ID - unique per kiosk session
  const [sessionId] = useState(() => crypto.randomUUID());
  
  // State
  const [events, setEvents] = useState<any[]>([]);
  const [isListening, setIsListening] = useState(false);

  // ⭐ CRITICAL: Subscribe to real-time updates
  useEffect(() => {
    const channel = supabase
      .channel(`session:${sessionId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'kiosk_results',
          filter: `session_id=eq.${sessionId}`,
        },
        (payload) => {
          console.log('✅ Results received!', payload);
          const results = payload.new.results;
          setEvents(results.events || []);
          setIsListening(false);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [sessionId]);

  // Start ElevenLabs conversation
  const startConversation = async () => {
    setIsListening(true);
    setEvents([]);

    // Start ElevenLabs with session_id
    // @ts-ignore
    await window.elevenlabs?.startConversation({
      agentId: process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID,
      variables: {
        session_id: sessionId,
        hotel_id: params.hotelId,
        api_url: process.env.NEXT_PUBLIC_API_URL
      }
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Voice Button */}
      <div className="text-center mb-8">
        <button
          onClick={startConversation}
          disabled={isListening}
          className={`
            px-12 py-6 rounded-full text-2xl font-bold
            ${isListening 
              ? 'bg-red-500 animate-pulse' 
              : 'bg-blue-600 hover:bg-blue-700'
            }
            text-white shadow-lg transition-all
          `}
        >
          {isListening ? '🎤 Listening...' : '🗣️ Tap to Speak'}
        </button>
      </div>

      {/* Events Grid */}
      {events.length > 0 && (
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">
            Found {events.length} results:
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {events.map((event: any, i: number) => (
              <div key={i} className="bg-white rounded-lg shadow-lg p-6">
                {/* Hotel Service Badge */}
                {event.event_details.is_hotel_service && (
                  <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">
                    🏨 Hotel Service
                  </span>
                )}
                
                {/* Distance */}
                {event.event_details.distance_km !== undefined && (
                  <span className="bg-green-100 text-green-800 text-xs font-bold px-2 py-1 rounded ml-2">
                    {event.event_details.distance_km === 0 
                      ? '📍 Here' 
                      : `📍 ${event.event_details.distance_km}km`
                    }
                  </span>
                )}

                <h3 className="text-xl font-bold mt-3">
                  {event.event_details.name}
                </h3>
                
                <p className="text-gray-700 my-3">
                  {event.suggestion}
                </p>

                <div className="text-sm text-gray-600 space-y-1">
                  <p>📍 {event.event_details.location}</p>
                  <p>📅 {event.event_details.date}</p>
                  <p>🕐 {event.event_details.time}</p>
                  <p className="font-bold">💰 {event.event_details.price}</p>
                </div>

                <button className="mt-4 w-full bg-green-600 text-white py-2 rounded hover:bg-green-700">
                  📱 Send to Phone
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug Panel (remove in production) */}
      <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded text-xs">
        <p>Session: {sessionId.slice(0, 8)}...</p>
        <p>Hotel: {params.hotelId}</p>
        <p>Events: {events.length}</p>
      </div>
    </div>
  );
}
```

---

### **5. Configure ElevenLabs Agent** (2 minutes)

In ElevenLabs Dashboard:

**Webhook URL:**
```
{{api_url}}/api/event/by-interests?session_id={{session_id}}
```

**Request Body:**
```json
{
  "interests": "{{extracted_interests}}",
  "hotel_id": "{{hotel_id}}"
}
```

**Variables to pass from frontend:**
- `session_id` - Generated in Next.js
- `hotel_id` - From URL params
- `api_url` - Your API URL

---

## 🔑 **IMPORTANT: How session_id Flows Through the System**

### **Understanding the Architecture**

**Question:** *"How does ElevenLabs know the session_id? It's generated in Next.js!"*

**Answer:** You **pass it to ElevenLabs** when starting the conversation!

---

### **The Complete Flow:**

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1: Next.js Generates session_id                   │
│  const sessionId = crypto.randomUUID()                  │
│  → Result: "f47ac10b-58cc-4372-a567-0e02b2c3d479"       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Pass to ElevenLabs via "variables"
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 2: Next.js Starts ElevenLabs Conversation         │
│                                                          │
│  elevenlabs.startConversation({                         │
│    agentId: 'agent-123',                                │
│    variables: {                                         │
│      session_id: "f47ac10b-58cc...",  ← Passed here!   │
│      hotel_id: "marriott-bangalore",                    │
│      api_url: "https://fastapi-project-tau.vercel.app"  │
│    }                                                    │
│  })                                                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ ElevenLabs stores these variables
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 3: ElevenLabs Stores Variables                    │
│                                                          │
│  Conversation Context:                                  │
│  {                                                      │
│    conversationId: "elevenlabs-conv-789",               │
│    variables: {                                         │
│      session_id: "f47ac10b-58cc...",  ← Stored!        │
│      hotel_id: "marriott-bangalore",                    │
│      api_url: "https://fastapi..."                      │
│    }                                                    │
│  }                                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Guest speaks
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 4: Guest Interaction                              │
│                                                          │
│  Guest: "I want comedy shows tonight"                   │
│                                                          │
│  Agent extracts: interests = "comedy shows"             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Build webhook call using variables
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 5: ElevenLabs Builds Webhook URL                  │
│                                                          │
│  Template:                                              │
│  {{api_url}}/api/event/by-interests?                    │
│  session_id={{session_id}}                              │
│                                                          │
│  Replace variables:                                     │
│  {{api_url}} → "https://fastapi-project-tau.vercel.app" │
│  {{session_id}} → "f47ac10b-58cc..."                    │
│                                                          │
│  Final URL:                                             │
│  https://fastapi-project-tau.vercel.app/                │
│  api/event/by-interests?session_id=f47ac10b-58cc...     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Make HTTP POST request
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 6: FastAPI Receives Request                       │
│                                                          │
│  Query Params:                                          │
│  - session_id = "f47ac10b-58cc..."  ← Got it!          │
│                                                          │
│  Body:                                                  │
│  {                                                      │
│    "interests": "comedy shows",                         │
│    "hotel_id": "marriott-bangalore"                     │
│  }                                                      │
│                                                          │
│  Process:                                               │
│  1. Find comedy events                                  │
│  2. Get hotel services                                  │
│  3. Generate results                                    │
│  4. Write to Supabase:                                  │
│     INSERT INTO kiosk_results                           │
│     (session_id, results)                               │
│     VALUES ('f47ac10b-58cc...', {...})                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Supabase broadcasts INSERT
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 7: Supabase Real-Time Broadcast                   │
│                                                          │
│  Event: INSERT on kiosk_results                         │
│  Data: session_id = "f47ac10b-58cc..."                  │
│                                                          │
│  Broadcast to all subscribers ──────────────┐           │
└─────────────────────────────────────────────┼───────────┘
                                              │
                                              │ WebSocket push
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 8: Next.js Receives Update                        │
│                                                          │
│  Subscription filter: session_id=eq.f47ac10b-58cc...    │
│  ✅ Match! This is for our session!                     │
│                                                          │
│  setEvents(payload.new.results.events)                  │
│  → Event cards appear on screen! 🎉                     │
│                                                          │
│  Time elapsed: ~50-150ms (real-time!)                   │
└─────────────────────────────────────────────────────────┘
```

---

### **Key Points:**

1. **Next.js owns the session_id**
   - Generated once per kiosk session
   - Passed to ElevenLabs when starting conversation

2. **ElevenLabs acts as a carrier**
   - Receives session_id from Next.js
   - Stores it as a "conversation variable"
   - Passes it to FastAPI in webhook URL

3. **FastAPI uses it to write results**
   - Receives session_id as query parameter
   - Writes to database with that session_id
   - Supabase broadcasts to correct subscriber

4. **Next.js receives results**
   - Subscription filters by session_id
   - Only receives results for its own session
   - Updates UI in real-time

---

### **Why This Works:**

✅ **Unique per kiosk** - Each tablet has its own session  
✅ **No conflicts** - Multiple kiosks work independently  
✅ **Real-time** - Results appear as they're generated  
✅ **Secure** - Each session only sees its own results  
✅ **Simple** - Just one variable to pass!  

---

### **Example with Multiple Kiosks:**

```
Kiosk 1 (Lobby):
  session_id: "aaa-111"
  Guest searches: "comedy"
  → Results written with session_id="aaa-111"
  → Only Kiosk 1 receives these results ✅

Kiosk 2 (Floor 3):
  session_id: "bbb-222"
  Guest searches: "spa"
  → Results written with session_id="bbb-222"
  → Only Kiosk 2 receives these results ✅

No interference! Each kiosk independent! 🎯
```

---

## 💻 **Practical Code Example**

### **Complete Working Example:**

```typescript
// app/kiosk/[hotelId]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export default function KioskPage({ params }: { params: { hotelId: string } }) {
  // ⭐ STEP 1: Generate unique session_id
  const [sessionId] = useState(() => {
    const id = crypto.randomUUID();
    console.log('🎯 Session created:', id);
    return id;
  });
  
  const [events, setEvents] = useState<any[]>([]);
  const [isListening, setIsListening] = useState(false);

  // ⭐ STEP 2: Subscribe to Supabase real-time
  useEffect(() => {
    console.log('📡 Subscribing to session:', sessionId);
    
    const channel = supabase
      .channel(`session:${sessionId}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'kiosk_results',
        filter: `session_id=eq.${sessionId}`,
      }, (payload) => {
        console.log('✅ Results received in real-time!');
        console.log('📦 Payload:', payload);
        
        const results = payload.new.results;
        setEvents(results.events || []);
        setIsListening(false);
      })
      .subscribe((status) => {
        console.log('📡 Subscription status:', status);
      });

    return () => {
      console.log('👋 Unsubscribing from session');
      supabase.removeChannel(channel);
    };
  }, [sessionId]);

  // ⭐ STEP 3: Start conversation and PASS session_id to ElevenLabs
  const startConversation = async () => {
    console.log('🎤 Starting conversation...');
    console.log('📤 Passing to ElevenLabs:', {
      session_id: sessionId,
      hotel_id: params.hotelId
    });
    
    setIsListening(true);
    setEvents([]);

    try {
      // @ts-ignore
      await window.elevenlabs.startConversation({
        agentId: process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID,
        
        // ⭐⭐⭐ THIS IS THE CRITICAL PART! ⭐⭐⭐
        // These variables are passed to ElevenLabs and used in webhook
        variables: {
          session_id: sessionId,        // ← ElevenLabs will use this in webhook!
          hotel_id: params.hotelId,     // ← And this!
          api_url: process.env.NEXT_PUBLIC_API_URL
        }
      });
      
      console.log('✅ Conversation started with session_id passed!');
    } catch (error) {
      console.error('❌ Failed to start conversation:', error);
      setIsListening(false);
    }
  };

  return (
    <div className="p-8">
      {/* Debug Info - shows flow is working */}
      <div className="mb-4 p-4 bg-gray-100 rounded">
        <p className="text-sm"><strong>Session ID:</strong> {sessionId}</p>
        <p className="text-sm"><strong>Hotel ID:</strong> {params.hotelId}</p>
        <p className="text-sm"><strong>Status:</strong> {isListening ? '🎤 Listening' : '✅ Ready'}</p>
        <p className="text-sm"><strong>Events:</strong> {events.length}</p>
      </div>

      <button
        onClick={startConversation}
        className="px-8 py-4 bg-blue-600 text-white rounded-lg"
      >
        {isListening ? '🎤 Listening...' : '🗣️ Tap to Speak'}
      </button>

      {/* Results */}
      <div className="mt-8 grid gap-4">
        {events.map((event, i) => (
          <div key={i} className="p-4 bg-white rounded shadow">
            <h3 className="font-bold">{event.event_details.name}</h3>
            <p>{event.suggestion}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**What happens when you run this:**

1. Page loads → session_id generated
2. Supabase subscription starts
3. Guest clicks button → ElevenLabs starts
4. **Session_id is passed to ElevenLabs**
5. Guest speaks → ElevenLabs calls webhook with session_id
6. FastAPI writes results with that session_id
7. Supabase broadcasts → Your subscription receives it
8. Cards appear! ⚡

---

## 🧪 Testing (2 minutes)

### **Test 1: Backend**

```bash
curl -X POST "https://your-api.vercel.app/api/event/by-interests?session_id=test-123" \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy", "hotel_id": "marriott-bangalore"}'

# Check Supabase table - should see row with session_id="test-123"
```

### **Test 2: Frontend**

1. Open kiosk page in browser
2. Open browser console
3. Click "Tap to Speak"
4. Say something
5. Watch console log: "✅ Results received!"
6. See cards appear on screen

---

## ⚙️ **ElevenLabs Agent Configuration (Detailed)**

### **Step-by-Step ElevenLabs Setup:**

**1. Go to ElevenLabs Dashboard → Your Agent → Configure**

**2. Add Custom Variables:**
```
In the "Variables" section, click "Add Variable":

Variable 1:
  Name: session_id
  Type: string
  Required: Yes
  Description: Unique session ID from kiosk frontend

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

**3. Configure Webhook/Tool:**
```
Tool Name: search_events
Description: Search for events based on guest interests

HTTP Method: POST
URL: {{api_url}}/api/event/by-interests?session_id={{session_id}}

Headers:
  Content-Type: application/json

Request Body:
{
  "interests": "{{extracted_interests}}",
  "hotel_id": "{{hotel_id}}"
}

Response Handling:
  The agent should read the "events" array and tell the guest about them.
```

**4. Update Agent Prompt:**
```
You are a helpful hotel concierge assistant.

You have access to these variables:
- session_id: Unique session identifier (automatically passed)
- hotel_id: Current hotel location
- api_url: Backend API URL

When a guest tells you what they're interested in:
1. Extract their interests (e.g., "comedy shows", "spa", "food")
2. Call the search_events tool with the extracted interests
3. The tool will return matching events and hotel services
4. Tell the guest about the results in a friendly, conversational way

Important: The session_id is already configured in the webhook - you don't need to mention it to guests.
```

**5. Test in ElevenLabs:**
```
In the test panel:
1. Set test values for variables:
   - session_id: "test-123"
   - hotel_id: "marriott-bangalore"
   - api_url: "https://fastapi-project-tau.vercel.app"

2. Type: "I want comedy shows"

3. Check if webhook is called with correct URL:
   https://fastapi-project-tau.vercel.app/api/event/by-interests?session_id=test-123

4. Verify results are returned
```

---

## 🎯 **Important Notes for Frontend Team**

### **✅ DO:**
- Generate session_id in Next.js
- Pass session_id to ElevenLabs in `variables` object
- Subscribe to Supabase with filter on that session_id
- Keep session_id unique per kiosk session (use crypto.randomUUID())

### **❌ DON'T:**
- Don't try to pass session_id after conversation starts
- Don't share session_id between multiple kiosks
- Don't use predictable session_ids (use UUIDs)
- Don't forget to unsubscribe on component unmount

---

## 🔍 **Debugging Guide**

### **Check 1: Is session_id being generated?**
```typescript
const [sessionId] = useState(() => {
  const id = crypto.randomUUID();
  console.log('🎯 Generated session_id:', id);  // Should see UUID
  return id;
});
```

### **Check 2: Is it being passed to ElevenLabs?**
```typescript
console.log('📤 Starting conversation with:', {
  session_id: sessionId,  // Should match generated UUID
  hotel_id: params.hotelId
});

await window.elevenlabs.startConversation({
  variables: { session_id: sessionId }  // Check this line!
});
```

### **Check 3: Is ElevenLabs calling webhook with session_id?**
```
Check FastAPI logs or Supabase api_logs table:
- Should see: ?session_id=abc-123-xyz in URL
- If missing → ElevenLabs not configured correctly
```

### **Check 4: Are results being written?**
```sql
-- In Supabase SQL Editor
SELECT * FROM kiosk_results 
ORDER BY created_at DESC 
LIMIT 10;

-- Should see rows with your session_ids
```

### **Check 5: Is subscription receiving?**
```typescript
.subscribe((status) => {
  console.log('📡 Status:', status);  
  // Should be: "SUBSCRIBED"
  // If "CHANNEL_ERROR" → Real-time not enabled
});
```

---

## 📞 **Quick Reference**

### **The Magic Line:**
```typescript
// This single line makes everything work:
variables: {
  session_id: sessionId,  // ← Pass to ElevenLabs
  hotel_id: params.hotelId
}
```

### **What ElevenLabs Does:**
1. Receives these variables from Next.js
2. Stores them for the conversation duration
3. Uses `{{session_id}}` in webhook URL
4. Replaces with actual value when making HTTP call
5. FastAPI receives it as query parameter

### **What Happens:**
```
Next.js:      session_id = "abc-123"
              ↓ (pass via variables)
ElevenLabs:   stores "abc-123"
              ↓ (uses in webhook)
FastAPI:      ?session_id=abc-123
              ↓ (writes to DB)
Supabase:     session_id = "abc-123"
              ↓ (broadcasts)
Next.js:      filter = "abc-123"
              ✅ Match! Display results!
```

---

## 🐛 Common Issues & Solutions

### **Issue 1: "No results appearing on screen"**

**Checklist:**
```typescript
// 1. Check session_id is generated
console.log('Session ID:', sessionId);  // Should see UUID

// 2. Check it's passed to ElevenLabs
console.log('Variables:', { session_id: sessionId });

// 3. Check subscription is active
.subscribe((status) => {
  console.log('Status:', status);  // Should be "SUBSCRIBED"
});

// 4. Check results are received
.on('postgres_changes', {}, (payload) => {
  console.log('Received:', payload);  // Should see data
});
```

**Most Common Cause:** Real-time not enabled in Supabase
**Solution:** Run `ALTER TABLE kiosk_results REPLICA IDENTITY FULL;`

---

### **Issue 2: "ElevenLabs not calling webhook with session_id"**

**Check ElevenLabs Configuration:**
```
❌ Wrong: {{session_id}}  (without api_url)
✅ Correct: {{api_url}}/api/event/by-interests?session_id={{session_id}}

❌ Wrong: Variables not defined in agent
✅ Correct: Add session_id as custom variable

❌ Wrong: Not passing variables when starting conversation
✅ Correct: variables: { session_id: sessionId }
```

**Test in ElevenLabs:**
- Set test values for variables
- Check webhook URL in logs
- Should see: `?session_id=test-123` in URL

---

### **Issue 3: "Results appear but for wrong session"**

**Check Filter Syntax:**
```typescript
// ❌ WRONG
filter: `session_id=${sessionId}`

// ✅ CORRECT (note the 'eq.')
filter: `session_id=eq.${sessionId}`
```

---

### **Issue 4: "Multiple kiosks seeing same results"**

**Cause:** Sharing session_id or wrong filter

**Solution:**
```typescript
// Generate NEW session_id per kiosk load
const [sessionId] = useState(() => crypto.randomUUID());

// NOT this (shares across page refreshes):
const sessionId = 'fixed-id';  // ❌ WRONG
```

---

### **Issue 5: "Subscription status: CHANNEL_ERROR"**

**Cause:** Real-time not enabled in Supabase

**Solution:**
1. Go to Supabase Dashboard
2. Database → Replication
3. Enable for `kiosk_results` table
4. Save and refresh your app

---

## 🧪 Quick Troubleshooting

### No results appearing?

```typescript
// Add debug logging
.on('postgres_changes', {
  // ... config
}, (payload) => {
  console.log('📦 Payload:', payload);  // Add this
  console.log('🎯 Results:', payload.new.results);  // And this
  setEvents(payload.new.results.events);
})
```

### Subscription not working?

Check browser console for:
```
✅ "Subscription status: SUBSCRIBED"
❌ "Subscription status: CHANNEL_ERROR" → Real-time not enabled
```

### ElevenLabs not passing session_id?

Check ElevenLabs logs for webhook URL:
```
✅ Should see: ?session_id=abc-123-xyz
❌ If missing: Variables not configured correctly
```

---

## 📊 Architecture Diagram

```
Your Next.js App
    │
    ├─ Generate session_id
    │
    ├─ Subscribe to Supabase ─────┐
    │                             │
    └─ Start ElevenLabs ──────────┼────┐
                                  │    │
                                  │    ▼
                              Supabase   ElevenLabs
                                  │         │
                                  │         ▼
                                  │    Calls FastAPI
                                  │         │
                                  │    ┌────┴────┐
                                  │    │ Results │
                                  │    └────┬────┘
                                  │         │
                                  │    Writes to DB
                                  │         │
                                  ▼◄────────┘
                              Real-time
                              Broadcast
                                  │
                                  ▼
                          Next.js receives
                          & displays cards
```

---

## 🎯 Key Points

1. **Session ID** - Links voice conversation to UI display
2. **Real-Time** - Results appear as they're generated
3. **Zero Cost** - Using Supabase (already have it)
4. **Fast** - 50-150ms broadcast latency
5. **Reliable** - Auto-reconnection built-in
6. **Scalable** - Handles 100+ concurrent sessions

---

## ✅ That's It!

**Total setup time:** 5-10 minutes  
**Code to write:** Copy-paste ready  
**Cost:** $0  
**Performance:** Excellent  

**You're ready to demo to Hotel GMs! 🎉**

---

## 📞 Need Help?

**Check:**
1. Browser console for errors
2. Supabase logs in dashboard
3. Network tab for subscription status
4. `REALTIME_SESSION_GUIDE.md` for detailed docs

**Debug command:**
```javascript
// In browser console
supabase.getChannels()  // See active subscriptions
```

---

## ✅ **Frontend Team Checklist**

### **Setup (One-time):**
- [ ] Install `@supabase/supabase-js`
- [ ] Add environment variables (.env.local)
- [ ] Create `lib/supabase.ts` with Supabase client
- [ ] Configure ElevenLabs agent with variables
- [ ] Configure webhook URL in ElevenLabs

### **Implementation (Per Page):**
- [ ] Generate session_id using `crypto.randomUUID()`
- [ ] Subscribe to Supabase real-time with filter
- [ ] Pass session_id to ElevenLabs in `variables` object
- [ ] Display events when subscription receives data
- [ ] Unsubscribe on component unmount

### **Testing:**
- [ ] Open browser console - see session_id logged
- [ ] Start conversation - see "SUBSCRIBED" status
- [ ] Speak to kiosk - see "Results received!" log
- [ ] Verify cards appear on screen
- [ ] Check Supabase table has rows
- [ ] Test with multiple kiosks (different sessions)

### **ElevenLabs Configuration:**
- [ ] Add custom variables (session_id, hotel_id, api_url)
- [ ] Set webhook URL with `{{session_id}}` parameter
- [ ] Update agent prompt
- [ ] Test in ElevenLabs dashboard
- [ ] Verify webhook is called with session_id

---

## 🎯 **Critical Code Snippets**

### **1. Generate session_id (once per kiosk load):**
```typescript
const [sessionId] = useState(() => crypto.randomUUID());
```

### **2. Pass to ElevenLabs (when starting conversation):**
```typescript
await window.elevenlabs.startConversation({
  agentId: 'your-agent-id',
  variables: {
    session_id: sessionId,  // ⭐ THIS IS KEY!
    hotel_id: params.hotelId
  }
});
```

### **3. Subscribe to real-time (filter by session_id):**
```typescript
supabase
  .channel(`session:${sessionId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'kiosk_results',
    filter: `session_id=eq.${sessionId}`  // ⭐ THIS IS KEY!
  }, (payload) => {
    setEvents(payload.new.results.events);
  })
  .subscribe();
```

---

## 📞 **Support & Documentation**

**For detailed technical docs:**
- See: `REALTIME_SESSION_GUIDE.md`

**For backend API reference:**
- See: `README.md`
- Or visit: https://your-api.vercel.app/docs

**For database setup:**
- See: `SUPABASE_SETUP.md`

**Need help?**
- Check browser console for errors
- Check Supabase logs
- Verify ElevenLabs webhook is called
- Test backend independently with curl

---

## 🎉 **You're All Set!**

**Summary:**
- ✅ Zero-cost real-time communication
- ✅ 50-150ms latency (instant!)
- ✅ Works with multiple kiosks
- ✅ Production-ready
- ✅ Complete documentation

**The secret sauce:** Pass `session_id` in the `variables` object! 🔑

---

**Happy Coding! 🚀**

