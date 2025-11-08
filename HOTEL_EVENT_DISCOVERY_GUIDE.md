# 🎯 Hotel-Specific Event Discovery Guide

Complete guide for using hotel-based event filtering in Spotive API.

---

## 🚀 What's New

The `/api/event/by-interests` endpoint now supports **hotel-specific filtering**! When you provide a `hotel_id`, the system will:

1. ✅ **Prioritize hotel services** - Spa, restaurant, bar shown first
2. ✅ **Filter by location** - Only events within hotel's search radius
3. ✅ **Sort by distance** - Closest events first
4. ✅ **Add distance info** - Each event shows distance from hotel

---

## 📡 API Usage

### **Basic Request (No Hotel)**

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "music, food"
  }'
```

**Result:** All music and food events in database

---

### **Hotel-Specific Request** ⭐ NEW!

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "food, entertainment",
    "hotel_id": "marriott-bangalore"
  }'
```

**Result:**
1. Marriott's restaurant (in-house service)
2. Nearby food events within 10km
3. All sorted by distance

---

### **Full Example with User Tracking**

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "spa, relaxation",
    "hotel_id": "marriott-bangalore",
    "phone_number": "+916362260992"
  }'
```

**Result:**
- Hotel services + nearby events
- User preferences tracked
- Distance information included

---

## 📊 Response Format

### **Without Hotel Filtering**

```json
{
  "success": true,
  "interests": "food",
  "mapped_categories": ["food"],
  "total_matching_events": 8,
  "returned_events": 5,
  "hotel_filtered": false,
  "events": [...]
}
```

### **With Hotel Filtering** ⭐

```json
{
  "success": true,
  "interests": "food, spa",
  "mapped_categories": ["food", "entertainment"],
  "total_matching_events": 12,
  "returned_events": 5,
  "hotel_filtered": true,
  "hotel": {
    "id": "uuid-here",
    "name": "Marriott Hotel Bangalore",
    "slug": "marriott-bangalore",
    "location": "Bangalore",
    "search_radius_km": 10
  },
  "hotel_services_count": 2,
  "events": [
    {
      "suggestion": "Check out M Café at Marriott...",
      "event_details": {
        "id": "service-uuid",
        "name": "M Café",
        "category": "food",
        "location": "Marriott Hotel Bangalore - Whitefield",
        "date": "Available daily",
        "time": "6:30 AM - 11:00 PM",
        "price": "₹2500 - ₹6000",
        "is_hotel_service": true,
        "service_type": "restaurant",
        "distance_km": 0
      }
    },
    {
      "suggestion": "There's a Food Festival at...",
      "event_details": {
        "id": "event-uuid",
        "name": "Bangalore Food Festival",
        "category": "food",
        "location": "Whitefield, Bangalore",
        "date": "2025-11-15",
        "time": "6:00 PM",
        "price": "₹500",
        "is_hotel_service": false,
        "distance_km": 2.5
      }
    }
  ]
}
```

---

## 🎯 How It Works

### **Step 1: Map Interests to Categories**

```
User searches: "relaxation, wellness"
→ AI maps to: ["entertainment"] (for spa services)
```

### **Step 2: Get Hotel Services**

```
Query hotel_services table:
→ Find: "Quan Spa" (service_type: spa)
→ Map spa → "entertainment" category
→ Format as event object
```

### **Step 3: Get External Events**

```
Query events table:
→ Find all "entertainment" events
→ Calculate distance from hotel (lat/long)
→ Filter: Only within 10km radius
```

### **Step 4: Combine & Sort**

```
Results:
1. Quan Spa (distance: 0km) - Hotel service
2. Comedy Show (distance: 2.3km)
3. Music Concert (distance: 5.1km)
4. Theater Show (distance: 8.7km)
```

---

## 🗺️ Distance Calculation

### **If Hotel & Event Have Coordinates:**

```python
# Haversine formula
Hotel: lat=12.9926, lon=77.7499 (Marriott Bangalore)
Event: lat=12.9716, lon=77.5946 (MG Road)

Distance = 13.8 km ❌ Outside 10km radius
→ Event filtered out
```

### **Fallback: City Name Matching**

If no coordinates available:

```python
Hotel city: "Bangalore"
Event location: "Indiranagar, Bangalore"

Match found ✅
Distance: null (unknown)
→ Event included but sorted last
```

---

## 🏨 Service Type → Category Mapping

| Service Type | Maps to Category | Example |
|-------------|------------------|---------|
| `spa` | `entertainment` | Quan Spa |
| `restaurant` | `food` | M Café |
| `bar` | `entertainment` | Alto Vino |
| `gym` | `sports` | Fitness Center |
| `pool` | `outdoor` | Swimming Pool |
| `tour` | `outdoor` | City Tours |
| `cab` | `entertainment` | Airport Transfer |
| `room_service` | `food` | In-Room Dining |

---

## 📝 Testing Scenarios

### **Scenario 1: Guest Searches for Food**

```bash
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "food, dining",
    "hotel_id": "marriott-bangalore"
  }'
```

**Expected Results:**
1. M Café (Marriott restaurant) - 0km
2. Nearby food festivals - sorted by distance
3. Max 5 results total

---

### **Scenario 2: Guest Searches for Relaxation**

```bash
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "spa, massage, relaxation",
    "hotel_id": "marriott-bangalore"
  }'
```

**Expected Results:**
1. Quan Spa (Marriott spa) - 0km
2. Any nearby wellness events

---

### **Scenario 3: No Hotel Services Match**

```bash
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "comedy shows",
    "hotel_id": "marriott-bangalore"
  }'
```

**Expected Results:**
- No hotel services (Marriott has no comedy service)
- Only nearby comedy events
- Sorted by distance

---

### **Scenario 4: Invalid Hotel ID**

```bash
curl -X POST http://localhost:8000/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{
    "interests": "music",
    "hotel_id": "non-existent-hotel"
  }'
```

**Expected Results:**
- Hotel not found → ignored
- Falls back to normal search
- All music events returned (not filtered)

---

## 🔧 Frontend Integration

### **Kiosk Initialization**

```javascript
// Frontend gets hotel slug from URL or config
const hotelSlug = "marriott-bangalore";

// All searches include hotel_id
async function searchEvents(interests) {
  const response = await fetch('/api/event/by-interests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      interests: interests,
      hotel_id: hotelSlug
    })
  });
  
  const data = await response.json();
  
  // Display results
  displayEvents(data.events);
  
  // Show hotel services badge
  if (data.hotel_services_count > 0) {
    showBadge(`${data.hotel_services_count} hotel services`);
  }
}
```

### **Displaying Distance**

```javascript
function renderEventCard(event) {
  const details = event.event_details;
  
  let distanceLabel = '';
  if (details.is_hotel_service) {
    distanceLabel = '<span class="badge">Hotel Service</span>';
  } else if (details.distance_km !== null) {
    distanceLabel = `<span class="distance">${details.distance_km} km away</span>`;
  }
  
  return `
    <div class="event-card">
      <h3>${details.name}</h3>
      <p>${event.suggestion}</p>
      ${distanceLabel}
      <button>Send to WhatsApp</button>
    </div>
  `;
}
```

---

## ⚙️ Configuration

### **Hotel Search Radius**

Default: 10km

Change via hotel settings:

```bash
curl -X PUT https://your-api.vercel.app/api/hotels/marriott-bangalore \
  -H "Content-Type: application/json" \
  -d '{"search_radius_km": 15}'
```

Now all searches for this hotel will filter events within 15km.

---

### **Hotel Coordinates**

For accurate distance calculation, set hotel coordinates:

```bash
curl -X PUT https://your-api.vercel.app/api/hotels/marriott-bangalore \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 12.9926,
    "longitude": 77.7499
  }'
```

**How to get coordinates:**
1. Google Maps → Right-click hotel location
2. Click coordinates to copy
3. First number = latitude, second = longitude

---

## 🎯 Benefits

### **For Guests:**
✅ See hotel services alongside external events  
✅ Discover nearby attractions automatically  
✅ Know exact distances to plan better  
✅ Hotel services appear first (convenience)  

### **For Hotels:**
✅ Upsell in-house services naturally  
✅ Promote spa, restaurant, bar seamlessly  
✅ Guests discover services while exploring  
✅ Increased service bookings  

### **For Developers:**
✅ Simple API - just add `hotel_id`  
✅ Backward compatible  
✅ Automatic distance calculation  
✅ Clean, consistent response format  

---

## 🐛 Troubleshooting

### Issue: Hotel services not showing

**Check:**
1. Hotel services exist: `GET /api/hotels/{hotel_id}/services`
2. Services are active: `is_active=true`
3. Services match interests: e.g., searching "music" won't show spa

---

### Issue: No distance information

**Cause:** Hotel or events don't have coordinates

**Solution:**
1. Add hotel coordinates via `/api/hotels/{id}` PUT
2. Add event coordinates in events table
3. Fallback: City name matching still works

---

### Issue: Too many/few results

**Adjust:**
- Increase `search_radius_km` for more results
- Decrease for fewer, closer results
- Default 10km is balanced for cities

---

## 📊 Testing Checklist

- [ ] Search without hotel_id (backward compatible)
- [ ] Search with valid hotel_id
- [ ] Search with invalid hotel_id (graceful fallback)
- [ ] Hotel service appears first
- [ ] Distance calculated correctly
- [ ] Events sorted by distance
- [ ] Services mapped to correct categories
- [ ] Response includes hotel info
- [ ] Works with phone_number tracking
- [ ] Works with all interest types

---

## 🚀 Next Steps

1. ✅ Test with Marriott Bangalore
2. ✅ Add more hotel services
3. ✅ Add coordinates to events
4. ✅ Test distance filtering
5. ⏭️ Build frontend UI to display results
6. ⏭️ Add session tracking
7. ⏭️ Add analytics dashboard

---

**Hotel-Specific Event Discovery is Ready! 🏨🎉**

