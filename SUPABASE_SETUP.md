# Supabase Database Setup for Hotel Kiosk System

This document contains the SQL commands to create the required tables for the Hotel Kiosk system.

## Prerequisites

- Access to your Supabase project dashboard
- Go to: **SQL Editor** in your Supabase dashboard

---

## 🏨 Hotel Management Tables

### Table 1: `hotels`

Stores hotel information and branding configuration.

```sql
CREATE TABLE hotels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,  -- URL-friendly identifier
    location_city TEXT NOT NULL,
    location_area TEXT,
    address TEXT,
    country_code TEXT DEFAULT 'IN',  -- ISO country code
    timezone TEXT DEFAULT 'Asia/Kolkata',
    
    -- Branding & Configuration
    logo_url TEXT,
    brand_colors JSONB DEFAULT '{"primary": "#000000", "secondary": "#FFFFFF"}'::jsonb,
    theme_config JSONB DEFAULT '{}'::jsonb,
    
    -- Location Settings
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    search_radius_km INTEGER DEFAULT 10,  -- Default search radius for nearby events
    
    -- Status & Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX idx_hotels_slug ON hotels(slug);
CREATE INDEX idx_hotels_location_city ON hotels(location_city);
CREATE INDEX idx_hotels_is_active ON hotels(is_active);
CREATE INDEX idx_hotels_created_at ON hotels(created_at DESC);
```

**Columns:**
- `id`: Unique hotel identifier (UUID)
- `slug`: URL-friendly identifier (e.g., "taj-mumbai")
- `location_city`: City where hotel is located
- `location_area`: Specific area/neighborhood
- `brand_colors`: JSONB with primary/secondary colors
- `search_radius_km`: How far to search for nearby events (default 10km)
- `is_active`: Whether kiosk is currently operational

---

### Table 2: `hotel_services`

Stores in-house hotel services for upselling (spa, restaurant, bar, tours, etc.)

```sql
CREATE TABLE hotel_services (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    
    -- Service Information
    service_type TEXT NOT NULL,  -- 'spa', 'restaurant', 'bar', 'tour', 'cab', 'room_service', 'gym'
    name TEXT NOT NULL,
    description TEXT,
    short_description TEXT,  -- For card display
    
    -- Pricing & Availability
    price_range TEXT,  -- e.g., "₹2000 - ₹5000"
    price_min DECIMAL(10, 2),
    price_max DECIMAL(10, 2),
    currency TEXT DEFAULT 'INR',
    available_hours TEXT,  -- e.g., "10:00 AM - 10:00 PM"
    
    -- Media & Booking
    image_url TEXT,
    booking_link TEXT,
    phone_number TEXT,
    
    -- Display Settings
    is_featured BOOLEAN DEFAULT false,  -- Show prominently
    display_order INTEGER DEFAULT 0,    -- Sort order
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX idx_hotel_services_hotel_id ON hotel_services(hotel_id);
CREATE INDEX idx_hotel_services_service_type ON hotel_services(service_type);
CREATE INDEX idx_hotel_services_is_featured ON hotel_services(is_featured);
CREATE INDEX idx_hotel_services_display_order ON hotel_services(display_order);
```

**Service Types:**
- `spa` - Spa services, massages, treatments
- `restaurant` - In-house dining, room service
- `bar` - Bar, lounge, happy hour
- `tour` - Hotel-organized tours, experiences
- `cab` - Cab booking, airport transfers
- `room_service` - Food delivery to room
- `gym` - Fitness center, yoga classes
- `pool` - Pool access, poolside service
- `other` - Custom services

---

### Table 3: `kiosk_results`

Stores real-time results for kiosk sessions (enables Next.js to display results).

```sql
CREATE TABLE kiosk_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_kiosk_results_session ON kiosk_results(session_id);
CREATE INDEX idx_kiosk_results_created ON kiosk_results(created_at DESC);

-- Enable Supabase Real-Time (CRITICAL!)
ALTER TABLE kiosk_results REPLICA IDENTITY FULL;

-- Auto-cleanup function (delete results older than 1 hour)
CREATE OR REPLACE FUNCTION cleanup_old_kiosk_results()
RETURNS void AS $$
BEGIN
    DELETE FROM kiosk_results
    WHERE created_at < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;
```

**Purpose:** 
- Temporary storage for event search results
- Enables real-time push to Next.js frontend
- Auto-cleanup keeps database clean
- Each session gets its own results

**Important:** Run `ALTER TABLE kiosk_results REPLICA IDENTITY FULL;` to enable real-time subscriptions!

---

### Table 4: `hotel_kiosk_sessions` (Optional - Analytics)

Tracks guest interactions with the kiosk for analytics.

```sql
CREATE TABLE hotel_kiosk_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    
    -- Session Information
    session_id TEXT,  -- Frontend-generated session ID
    session_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Guest Interaction
    guest_interests TEXT,
    mapped_categories JSONB,
    results_shown JSONB,  -- Array of event/service IDs shown
    
    -- Actions
    whatsapp_sent BOOLEAN DEFAULT false,
    items_shared_count INTEGER DEFAULT 0,
    
    -- Settings
    language TEXT DEFAULT 'en',
    voice_enabled BOOLEAN DEFAULT false,
    
    -- Performance
    duration_seconds INTEGER,
    
    -- Metadata
    user_agent TEXT,
    device_info JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX idx_kiosk_sessions_hotel_id ON hotel_kiosk_sessions(hotel_id);
CREATE INDEX idx_kiosk_sessions_timestamp ON hotel_kiosk_sessions(session_timestamp DESC);
CREATE INDEX idx_kiosk_sessions_whatsapp ON hotel_kiosk_sessions(whatsapp_sent);
```

**Purpose:** Analytics and tracking for hotel operators to see:
- How many guests use the kiosk
- What they search for
- Conversion rates (WhatsApp shares)
- Popular interests per hotel

---

## 📊 Events Table Update

Update the existing `events` table to support hotel-specific filtering and location tracking:

```sql
-- Add hotel relationship columns to events table
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS hotel_id UUID REFERENCES hotels(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS is_hotel_service BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS service_type TEXT,
ADD COLUMN IF NOT EXISTS distance_from_hotel_km DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8),
ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_events_hotel_id ON events(hotel_id);
CREATE INDEX IF NOT EXISTS idx_events_is_hotel_service ON events(is_hotel_service);
CREATE INDEX IF NOT EXISTS idx_events_location ON events(latitude, longitude);
```

**New Columns:**
- `hotel_id`: Link event to specific hotel (NULL = general event)
- `is_hotel_service`: True if this is an in-house service (vs external event)
- `service_type`: Type if it's a hotel service (spa, restaurant, etc.)
- `distance_from_hotel_km`: Pre-calculated distance for sorting
- `latitude`: Event latitude for distance calculation
- `longitude`: Event longitude for distance calculation

---

## 📍 Adding Location Data to Existing Events

If you have existing events, you can add coordinates manually or in bulk:

### **Method 1: Manual Update (Single Event)**

```sql
-- Update a specific event with coordinates
UPDATE events
SET 
    latitude = 12.9716,
    longitude = 77.5946
WHERE name = 'Sunburn Music Festival';
```

### **Method 2: Bulk Update by Location String**

For events in well-known locations:

```sql
-- Palace Grounds, Bangalore
UPDATE events
SET latitude = 13.0155, longitude = 77.5696
WHERE location LIKE '%Palace Grounds%';

-- Indiranagar, Bangalore  
UPDATE events
SET latitude = 12.9716, longitude = 77.6412
WHERE location LIKE '%Indiranagar%';

-- Koramangala, Bangalore
UPDATE events
SET latitude = 12.9352, longitude = 77.6245
WHERE location LIKE '%Koramangala%';

-- Whitefield, Bangalore
UPDATE events
SET latitude = 12.9698, longitude = 77.7499
WHERE location LIKE '%Whitefield%';

-- MG Road, Bangalore
UPDATE events
SET latitude = 12.9716, longitude = 77.5946
WHERE location LIKE '%MG Road%';

-- Nandi Hills
UPDATE events
SET latitude = 13.3704, longitude = 77.6839
WHERE location LIKE '%Nandi Hills%';
```

### **Method 3: Default to City Center (Fallback)**

For events without specific location:

```sql
-- Set Bangalore city center as default for events without coordinates
UPDATE events
SET latitude = 12.9716, longitude = 77.5946
WHERE latitude IS NULL 
  AND location LIKE '%Bangalore%';
```

---

## 👥 User Profiles Tables

### Table 4: `users`

Stores user profile information and accumulated preferences.

```sql
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_searches INTEGER DEFAULT 0,
    favorite_categories JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create index on phone_number for fast lookups
CREATE INDEX idx_users_phone_number ON users(phone_number);

-- Create index on last_active for analytics
CREATE INDEX idx_users_last_active ON users(last_active DESC);
```

**Columns:**
- `id`: Unique identifier (UUID)
- `phone_number`: Indian phone number in format +91XXXXXXXXXX (unique)
- `username`: User's display name
- `created_at`: When user registered
- `last_active`: Last time user made a search
- `total_searches`: Counter of total searches made
- `favorite_categories`: JSONB object storing category counts e.g., `{"comedy": 15, "sports": 8}`
- `metadata`: Flexible JSONB for future fields

---

## Table 2: `user_search_history`

Tracks every search a user makes.

```sql
CREATE TABLE user_search_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    mapped_categories JSONB NOT NULL,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    results_count INTEGER DEFAULT 0
);

-- Create index on user_id for fast user history lookups
CREATE INDEX idx_search_history_user_id ON user_search_history(user_id);

-- Create index on search_timestamp for sorting
CREATE INDEX idx_search_history_timestamp ON user_search_history(search_timestamp DESC);
```

**Columns:**
- `id`: Unique identifier
- `user_id`: Foreign key to users table
- `search_query`: Original interests string from user
- `mapped_categories`: JSONB array of categories e.g., `["comedy", "music"]`
- `search_timestamp`: When search was performed
- `results_count`: Number of events found

---

## Table 3: `user_preferences`

Stores manually set user preferences.

```sql
CREATE TABLE user_preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_categories JSONB DEFAULT '[]'::jsonb,
    preferred_locations JSONB DEFAULT '[]'::jsonb,
    preferred_time_slots JSONB DEFAULT '[]'::jsonb,
    price_range JSONB DEFAULT NULL,
    avoid_categories JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on user_id
CREATE INDEX idx_preferences_user_id ON user_preferences(user_id);
```

**Columns:**
- `id`: Unique identifier
- `user_id`: Foreign key to users table (one-to-one relationship)
- `preferred_categories`: Array of categories e.g., `["comedy", "outdoor"]`
- `preferred_locations`: Array of locations e.g., `["Indiranagar", "Koramangala"]`
- `preferred_time_slots`: Array of time preferences e.g., `["evening", "weekend"]`
- `price_range`: Object with min/max e.g., `{"min": 0, "max": 1500}`
- `avoid_categories`: Array of categories to avoid
- `updated_at`: Last update timestamp

---

## Enable Row Level Security (Optional but Recommended)

If you want to add security policies (for production):

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create policies (example - adjust based on your auth strategy)
-- Allow service role (your API) to do everything
CREATE POLICY "Service role can do everything on users"
ON users FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Service role can do everything on search_history"
ON user_search_history FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Service role can do everything on preferences"
ON user_preferences FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

---

## Verify Tables

Run this query to verify all tables were created:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'user_search_history', 'user_preferences');
```

You should see all 3 tables listed.

---

## Example Data (Optional - for testing)

```sql
-- Insert a test user
INSERT INTO users (phone_number, username, favorite_categories)
VALUES ('+919876543210', 'Test User', '{"comedy": 5, "music": 3}'::jsonb);

-- Insert test search history
INSERT INTO user_search_history (user_id, search_query, mapped_categories, results_count)
VALUES (
    (SELECT id FROM users WHERE phone_number = '+919876543210'),
    'comedy shows',
    '["comedy"]'::jsonb,
    5
);

-- Insert test preferences
INSERT INTO user_preferences (user_id, preferred_categories, preferred_locations)
VALUES (
    (SELECT id FROM users WHERE phone_number = '+919876543210'),
    '["comedy", "outdoor"]'::jsonb,
    '["Indiranagar", "Koramangala"]'::jsonb
);
```

---

## Testing the Setup

After creating the tables, test the API endpoints:

1. **Register a user:**
   ```bash
   POST http://your-api-url/api/users/register
   {
     "phone_number": "+919876543210",
     "username": "Ashok Kumar"
   }
   ```

2. **Make a search with tracking:**
   ```bash
   POST http://your-api-url/api/event/by-interests
   {
     "interests": "comedy",
     "phone_number": "+919876543210"
   }
   ```

3. **Get user profile:**
   ```bash
   GET http://your-api-url/api/users/+919876543210
   ```

4. **Check accumulated preferences:**
   After a few searches, check the `favorite_categories` field in the users table.

---

## Maintenance Queries

### View user statistics:
```sql
SELECT 
    username,
    phone_number,
    total_searches,
    favorite_categories,
    last_active
FROM users
ORDER BY total_searches DESC
LIMIT 10;
```

### View search trends:
```sql
SELECT 
    search_query,
    COUNT(*) as search_count,
    AVG(results_count) as avg_results
FROM user_search_history
GROUP BY search_query
ORDER BY search_count DESC
LIMIT 20;
```

### Clean up old search history (optional):
```sql
-- Delete search history older than 90 days
DELETE FROM user_search_history
WHERE search_timestamp < NOW() - INTERVAL '90 days';
```

---

## Migration Notes

If you already have an `events` table and `api_logs` table in your Supabase, these new tables will coexist peacefully. No changes to existing tables are required.

---

## Troubleshooting

**Error: "relation does not exist"**
- Make sure you ran the CREATE TABLE commands in the SQL Editor
- Check that you're using the correct schema (public)

**Error: "foreign key violation"**
- Make sure the `users` table exists before creating `user_search_history` or `user_preferences`
- Create tables in the order shown in this document

**Error: "duplicate key value"**
- Phone numbers must be unique
- Check if user already exists before trying to register again

---

## Next Steps

After setting up the database:

1. ✅ Test all API endpoints
2. ✅ Monitor the `favorite_categories` accumulation
3. ✅ Set up analytics on the `user_search_history` table
4. 🔜 Add push notifications for new matching events
5. 🔜 Build recommendation algorithms based on user data
