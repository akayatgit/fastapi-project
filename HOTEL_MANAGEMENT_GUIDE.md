# 🏨 Hotel Management API Guide

Complete guide for managing hotels and services in the Spotive Hotel Kiosk system.

---

## 🎯 Overview

The Hotel Management system enables multi-hotel support with white-label branding, in-house services, and per-hotel configuration. Each hotel can have custom branding, services (spa, restaurant, bar), and location-based event filtering.

---

## 📊 Database Tables

### 1. **hotels** - Hotel Information & Branding
- Hotel name, slug (URL-friendly ID)
- Location (city, area, lat/long)
- Branding (logo, colors, theme)
- Search radius for nearby events
- Active status

### 2. **hotel_services** - In-House Services
- Service type (spa, restaurant, bar, tour, cab, etc.)
- Name, description, pricing
- Booking links, phone numbers
- Featured status, display order

### 3. **hotel_kiosk_sessions** - Analytics Tracking
- Guest interactions per hotel
- Interests searched
- WhatsApp conversions
- Session duration

---

## 🚀 Setup Instructions

### Step 1: Create Database Tables

Run this SQL in Supabase SQL Editor:

```sql
-- 1. Hotels Table
CREATE TABLE hotels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    location_city TEXT NOT NULL,
    location_area TEXT,
    address TEXT,
    country_code TEXT DEFAULT 'IN',
    timezone TEXT DEFAULT 'Asia/Kolkata',
    
    logo_url TEXT,
    brand_colors JSONB DEFAULT '{"primary": "#000000", "secondary": "#FFFFFF"}'::jsonb,
    theme_config JSONB DEFAULT '{}'::jsonb,
    
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    search_radius_km INTEGER DEFAULT 10,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_hotels_slug ON hotels(slug);
CREATE INDEX idx_hotels_location_city ON hotels(location_city);
CREATE INDEX idx_hotels_is_active ON hotels(is_active);

-- 2. Hotel Services Table
CREATE TABLE hotel_services (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    
    service_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    short_description TEXT,
    
    price_range TEXT,
    price_min DECIMAL(10, 2),
    price_max DECIMAL(10, 2),
    currency TEXT DEFAULT 'INR',
    available_hours TEXT,
    
    image_url TEXT,
    booking_link TEXT,
    phone_number TEXT,
    
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_hotel_services_hotel_id ON hotel_services(hotel_id);
CREATE INDEX idx_hotel_services_service_type ON hotel_services(service_type);
CREATE INDEX idx_hotel_services_is_featured ON hotel_services(is_featured);

-- 3. Hotel Kiosk Sessions Table
CREATE TABLE hotel_kiosk_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    
    session_id TEXT,
    session_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    guest_interests TEXT,
    mapped_categories JSONB,
    results_shown JSONB,
    
    whatsapp_sent BOOLEAN DEFAULT false,
    items_shared_count INTEGER DEFAULT 0,
    
    language TEXT DEFAULT 'en',
    voice_enabled BOOLEAN DEFAULT false,
    
    duration_seconds INTEGER,
    
    user_agent TEXT,
    device_info JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_kiosk_sessions_hotel_id ON hotel_kiosk_sessions(hotel_id);
CREATE INDEX idx_kiosk_sessions_timestamp ON hotel_kiosk_sessions(session_timestamp DESC);

-- 4. Update Events Table (if exists)
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS hotel_id UUID REFERENCES hotels(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS is_hotel_service BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS service_type TEXT,
ADD COLUMN IF NOT EXISTS distance_from_hotel_km DECIMAL(5, 2);

CREATE INDEX IF NOT EXISTS idx_events_hotel_id ON events(hotel_id);
```

### Step 2: Disable Row Level Security (Quick Setup)

```sql
ALTER TABLE hotels DISABLE ROW LEVEL SECURITY;
ALTER TABLE hotel_services DISABLE ROW LEVEL SECURITY;
ALTER TABLE hotel_kiosk_sessions DISABLE ROW LEVEL SECURITY;
```

---

## 📡 API Endpoints

### **Hotel Management**

#### `POST /api/hotels` - Create Hotel

Create a new hotel in the system.

**Request:**
```json
{
  "name": "Taj Wellington Mews",
  "slug": "taj-mumbai",
  "location_city": "Mumbai",
  "location_area": "Colaba",
  "address": "123 MG Road, Mumbai",
  "logo_url": "https://example.com/logo.png",
  "brand_colors": {
    "primary": "#C4A962",
    "secondary": "#1A1A1A"
  },
  "theme_config": {},
  "latitude": 18.9220,
  "longitude": 72.8347,
  "search_radius_km": 15,
  "timezone": "Asia/Kolkata",
  "country_code": "IN",
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Hotel created successfully",
  "hotel": {
    "id": "uuid-here",
    "name": "Taj Wellington Mews",
    "slug": "taj-mumbai",
    ...
  }
}
```

**Example:**
```bash
curl -X POST https://your-api.vercel.app/api/hotels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Taj Mumbai",
    "slug": "taj-mumbai",
    "location_city": "Mumbai",
    "location_area": "Colaba",
    "brand_colors": {"primary": "#C4A962", "secondary": "#1A1A1A"},
    "latitude": 18.9220,
    "longitude": 72.8347
  }'
```

---

#### `GET /api/hotels` - List All Hotels

List all hotels with optional filtering.

**Query Parameters:**
- `is_active` (optional) - Filter by active status

**Response:**
```json
{
  "success": true,
  "count": 3,
  "hotels": [
    {
      "id": "uuid",
      "name": "Taj Mumbai",
      "slug": "taj-mumbai",
      "location_city": "Mumbai",
      "is_active": true,
      ...
    }
  ]
}
```

**Example:**
```bash
# Get all hotels
curl https://your-api.vercel.app/api/hotels

# Get only active hotels
curl https://your-api.vercel.app/api/hotels?is_active=true
```

---

#### `GET /api/hotels/{hotel_id}` - Get Hotel Details

Get specific hotel by ID or slug.

**Path Parameter:**
- `hotel_id` - Hotel UUID or slug

**Example:**
```bash
# By ID
curl https://your-api.vercel.app/api/hotels/uuid-here

# By slug
curl https://your-api.vercel.app/api/hotels/taj-mumbai
```

---

#### `PUT /api/hotels/{hotel_id}` - Update Hotel

Update hotel information (all fields optional).

**Request:**
```json
{
  "name": "Taj Wellington Mews Luxury",
  "logo_url": "https://new-logo.com/logo.png",
  "search_radius_km": 20,
  "is_active": true
}
```

**Example:**
```bash
curl -X PUT https://your-api.vercel.app/api/hotels/taj-mumbai \
  -H "Content-Type: application/json" \
  -d '{"search_radius_km": 20}'
```

---

#### `DELETE /api/hotels/{hotel_id}` - Deactivate Hotel

Soft delete (sets `is_active=false`).

**Example:**
```bash
curl -X DELETE https://your-api.vercel.app/api/hotels/taj-mumbai
```

---

#### `GET /api/hotels/{hotel_id}/config` - Get Kiosk Configuration

Get hotel configuration for frontend kiosk.

**Response:**
```json
{
  "success": true,
  "config": {
    "hotel_id": "uuid",
    "hotel_name": "Taj Mumbai",
    "slug": "taj-mumbai",
    "branding": {
      "logo_url": "https://...",
      "brand_colors": {
        "primary": "#C4A962",
        "secondary": "#1A1A1A"
      },
      "theme_config": {}
    },
    "location": {
      "city": "Mumbai",
      "area": "Colaba",
      "latitude": 18.9220,
      "longitude": 72.8347,
      "search_radius_km": 15
    },
    "settings": {
      "timezone": "Asia/Kolkata",
      "country_code": "IN",
      "is_active": true
    }
  }
}
```

**Example:**
```bash
curl https://your-api.vercel.app/api/hotels/taj-mumbai/config
```

---

### **Hotel Services Management**

#### `POST /api/hotels/{hotel_id}/services` - Create Service

Add a service to a hotel (spa, restaurant, bar, etc.).

**Request:**
```json
{
  "service_type": "spa",
  "name": "Jiva Spa",
  "short_description": "Rejuvenating spa treatments",
  "description": "Experience traditional Indian wellness at our world-class spa",
  "price_range": "₹3000 - ₹8000",
  "price_min": 3000,
  "price_max": 8000,
  "currency": "INR",
  "available_hours": "10:00 AM - 10:00 PM",
  "image_url": "https://example.com/spa.jpg",
  "booking_link": "https://hotel.com/spa/book",
  "phone_number": "+912212345678",
  "is_featured": true,
  "display_order": 1,
  "metadata": {}
}
```

**Service Types:**
- `spa` - Spa, massage, wellness
- `restaurant` - Dining, room service
- `bar` - Bar, lounge, drinks
- `tour` - Tours, experiences
- `cab` - Transportation, airport transfer
- `room_service` - Food delivery
- `gym` - Fitness, yoga
- `pool` - Pool, poolside service
- `other` - Custom services

**Example:**
```bash
curl -X POST https://your-api.vercel.app/api/hotels/taj-mumbai/services \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "spa",
    "name": "Jiva Spa",
    "short_description": "Traditional Indian wellness",
    "price_range": "₹3000 - ₹8000",
    "price_min": 3000,
    "price_max": 8000,
    "is_featured": true
  }'
```

---

#### `GET /api/hotels/{hotel_id}/services` - List Services

List all services for a hotel.

**Query Parameters:**
- `service_type` (optional) - Filter by type
- `is_featured` (optional) - Filter featured services
- `is_active` (optional, default: true) - Filter active services

**Response:**
```json
{
  "success": true,
  "count": 5,
  "services": [
    {
      "id": "uuid",
      "hotel_id": "hotel-uuid",
      "service_type": "spa",
      "name": "Jiva Spa",
      "short_description": "Rejuvenating spa treatments",
      "price_range": "₹3000 - ₹8000",
      "is_featured": true,
      "display_order": 1,
      ...
    }
  ]
}
```

**Examples:**
```bash
# Get all services
curl https://your-api.vercel.app/api/hotels/taj-mumbai/services

# Get only spa services
curl https://your-api.vercel.app/api/hotels/taj-mumbai/services?service_type=spa

# Get only featured services
curl https://your-api.vercel.app/api/hotels/taj-mumbai/services?is_featured=true
```

---

#### `PUT /api/hotels/{hotel_id}/services/{service_id}` - Update Service

Update a service (all fields optional).

**Example:**
```bash
curl -X PUT https://your-api.vercel.app/api/hotels/taj-mumbai/services/service-uuid \
  -H "Content-Type: application/json" \
  -d '{"is_featured": true, "display_order": 1}'
```

---

#### `DELETE /api/hotels/{hotel_id}/services/{service_id}` - Deactivate Service

Soft delete a service.

**Example:**
```bash
curl -X DELETE https://your-api.vercel.app/api/hotels/taj-mumbai/services/service-uuid
```

---

## 🎬 Complete Setup Example

### Scenario: Setting up "Taj Mumbai" hotel

```bash
# Step 1: Create the hotel
curl -X POST https://your-api.vercel.app/api/hotels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Taj Mumbai",
    "slug": "taj-mumbai",
    "location_city": "Mumbai",
    "location_area": "Colaba",
    "address": "Apollo Bunder, Mumbai 400001",
    "brand_colors": {"primary": "#C4A962", "secondary": "#1A1A1A"},
    "latitude": 18.9220,
    "longitude": 72.8347,
    "search_radius_km": 15
  }'

# Response: Save the hotel ID from response

# Step 2: Add Spa Service
curl -X POST https://your-api.vercel.app/api/hotels/taj-mumbai/services \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "spa",
    "name": "Jiva Spa",
    "short_description": "Traditional Indian spa experience",
    "price_range": "₹3000 - ₹8000",
    "price_min": 3000,
    "price_max": 8000,
    "available_hours": "10:00 AM - 10:00 PM",
    "is_featured": true,
    "display_order": 1
  }'

# Step 3: Add Restaurant
curl -X POST https://your-api.vercel.app/api/hotels/taj-mumbai/services \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "restaurant",
    "name": "Wasabi by Morimoto",
    "short_description": "Japanese fine dining",
    "price_range": "₹5000 - ₹12000",
    "price_min": 5000,
    "price_max": 12000,
    "available_hours": "7:00 PM - 11:30 PM",
    "booking_link": "https://taj.com/wasabi/book",
    "is_featured": true,
    "display_order": 2
  }'

# Step 4: Add Bar
curl -X POST https://your-api.vercel.app/api/hotels/taj-mumbai/services \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "bar",
    "name": "Harbour Bar",
    "short_description": "Cocktails with sea view",
    "price_range": "₹800 - ₹2500",
    "available_hours": "11:00 AM - 1:00 AM",
    "is_featured": false,
    "display_order": 3
  }'

# Step 5: Get hotel configuration for frontend
curl https://your-api.vercel.app/api/hotels/taj-mumbai/config

# Step 6: List all services
curl https://your-api.vercel.app/api/hotels/taj-mumbai/services
```

---

## 🎨 Branding Configuration

### Brand Colors Format

```json
{
  "primary": "#C4A962",    // Main brand color (buttons, headers)
  "secondary": "#1A1A1A",  // Secondary color (text, backgrounds)
  "accent": "#D4AF37",     // Optional accent color
  "background": "#FFFFFF"  // Optional background color
}
```

### Theme Config (Advanced)

```json
{
  "font_family": "Playfair Display",
  "font_size_base": "16px",
  "border_radius": "8px",
  "button_style": "rounded",
  "animation_speed": "300ms"
}
```

---

## 📊 Frontend Integration

### How the Frontend Uses This API:

1. **On Kiosk Load:**
   ```javascript
   // Frontend loads hotel config
   const config = await fetch('/api/hotels/taj-mumbai/config');
   // Apply branding (logo, colors, theme)
   applyBranding(config.branding);
   ```

2. **Display Services:**
   ```javascript
   // Get featured services for home screen
   const services = await fetch('/api/hotels/taj-mumbai/services?is_featured=true');
   // Show as cards on kiosk
   ```

3. **Event Discovery:**
   ```javascript
   // Use hotel location to filter nearby events
   const events = await fetch('/api/event/by-interests?hotel_id=taj-mumbai');
   ```

---

## 🔄 Migration from Old System

If you have existing events, no migration needed! Just:

1. Create hotel tables (SQL above)
2. Add your hotels via API
3. Add hotel services
4. Events continue to work as-is
5. Optionally link events to hotels later

---

## 🧪 Testing Checklist

- [ ] Create a hotel
- [ ] Get hotel by ID
- [ ] Get hotel by slug
- [ ] Update hotel branding
- [ ] Get hotel config
- [ ] Add spa service
- [ ] Add restaurant service
- [ ] Add bar service
- [ ] List all services
- [ ] List featured services
- [ ] Update service
- [ ] Deactivate service
- [ ] Deactivate hotel
- [ ] List all hotels

---

## 📈 Next Features (Coming Soon)

- [ ] Hotel-specific event filtering
- [ ] Analytics dashboard per hotel
- [ ] Hotel operator permissions
- [ ] Bulk import services
- [ ] Service availability calendar
- [ ] Multi-language service descriptions
- [ ] Service booking integration

---

## 🐛 Troubleshooting

### Error: "Hotel not found"
- Check if hotel exists: `GET /api/hotels`
- Verify you're using correct ID or slug

### Error: "Service not found"
- Verify service belongs to the hotel
- Check service is active: `?is_active=true`

### Error: Tables don't exist
- Run the SQL from Step 1 in Supabase
- Check RLS is disabled or policies are set

### Brand colors not applying
- Check JSON format is correct: `{"primary": "#000", "secondary": "#FFF"}`
- Frontend must read from `/config` endpoint

---

## 📄 Related Documentation

- `SUPABASE_SETUP.md` - Complete database schema
- `README.md` - Project overview
- `USER_PROFILES_API_GUIDE.md` - User management

---

**Hotel Management System Ready! 🏨✨**

