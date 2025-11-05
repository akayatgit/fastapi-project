# Supabase Database Setup for Spotive

## Overview
Spotive uses Supabase as its event database. This document explains how to set up your Supabase tables.

## Database Schema

### Events Table

Create a table named `events` with the following columns:

| Column Name | Data Type | Description | Required |
|------------|-----------|-------------|----------|
| `id` | `bigint` or `uuid` | Primary key, auto-increment | Yes |
| `name` | `text` | Event name | Yes |
| `category` | `text` | Event category (concert, sports, outdoor, food, spiritual, cultural, kids, entertainment) | Yes |
| `description` | `text` | Event description | Yes |
| `location` | `text` | Venue/location in Bangalore | Yes |
| `date` | `date` or `text` | Event date | Yes |
| `time` | `text` | Event time | Yes |
| `price` | `text` | Price or price range | Yes |
| `image_url` | `text` | URL to event image | No |
| `booking_link` | `text` | URL to booking page | No |
| `created_at` | `timestamp` | Auto-generated timestamp | No |

## SQL to Create Tables

### 1. Events Table

```sql
CREATE TABLE events (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  category text NOT NULL,
  description text NOT NULL,
  location text NOT NULL,
  date text NOT NULL,
  time text NOT NULL,
  price text NOT NULL,
  image_url text,
  booking_link text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Add index for category queries
CREATE INDEX idx_events_category ON events(category);
```

### 2. API Logs Table (For Analytics)

```sql
CREATE TABLE api_logs (
  id bigserial PRIMARY KEY,
  timestamp timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  endpoint text NOT NULL,
  interests text,
  mapped_categories jsonb,
  total_matching_events integer,
  selected_event_id bigint,
  selected_event_name text,
  selected_event_category text,
  success boolean NOT NULL,
  error_message text,
  response_time_ms numeric,
  client_ip text,
  user_agent text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Add indexes for faster analytics queries
CREATE INDEX idx_api_logs_timestamp ON api_logs(timestamp DESC);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_success ON api_logs(success);
CREATE INDEX idx_api_logs_interests ON api_logs(interests);
CREATE INDEX idx_api_logs_selected_event_id ON api_logs(selected_event_id);

-- Add comment
COMMENT ON TABLE api_logs IS 'Stores detailed logs of API calls for data analysis and debugging';
```

## Sample Data

Insert some sample events to test:

```sql
INSERT INTO events (name, category, description, location, date, time, price, image_url, booking_link)
VALUES
  ('Sunburn Music Festival', 'concert', 'Electronic dance music festival with international DJs', 'Palace Grounds, Bangalore', '2025-11-15', '18:00', '₹2000 - ₹5000', 'https://example.com/sunburn.jpg', 'https://bookmyshow.com/sunburn'),
  ('Bangalore Marathon', 'sports', 'Annual marathon event with 5K, 10K, and full marathon categories', 'Kanteerava Stadium, Bangalore', '2025-11-10', '06:00', '₹500 - ₹1500', 'https://example.com/marathon.jpg', 'https://bangaloremarathon.com'),
  ('Cubbon Park Food Festival', 'food', 'Weekend food festival featuring street food and buffet stalls', 'Cubbon Park, Bangalore', '2025-11-08', '12:00', 'Free entry, pay per stall', 'https://example.com/foodfest.jpg', 'https://cubbonparkfest.com'),
  ('Iskcon Janmashtami Celebration', 'spiritual', 'Grand celebration with bhajans, cultural programs, and prasadam', 'ISKCON Temple, Rajajinagar', '2025-11-12', '08:00', 'Free', 'https://example.com/janmashtami.jpg', 'https://iskconbangalore.org'),
  ('Rangoli Art Workshop', 'cultural', 'Traditional rangoli art workshop for all ages', 'Chitrakala Parishath, Bangalore', '2025-11-14', '10:00', '₹300', 'https://example.com/rangoli.jpg', 'https://chitrakalaparishath.com'),
  ('Kids Adventure Park Day', 'kids', 'Fun-filled day with rides, games, and activities for children', 'Wonderla Amusement Park, Bangalore', '2025-11-09', '10:00', '₹800 - ₹1200', 'https://example.com/wonderla.jpg', 'https://wonderla.com'),
  ('Nandi Hills Sunrise Trek', 'outdoor', 'Early morning trek to catch the beautiful sunrise at Nandi Hills', 'Nandi Hills, Bangalore', '2025-11-11', '04:30', '₹500', 'https://example.com/nandihills.jpg', 'https://bangaloretrekking.com'),
  ('Standup Comedy Night', 'entertainment', 'Evening of laughter with popular standup comedians', 'Koramangala Social, Bangalore', '2025-11-13', '20:00', '₹500', 'https://example.com/comedy.jpg', 'https://insider.in/comedy');
```

## API Endpoints

Once the table is set up, the following endpoints will work:

- `GET /api/random-event` - Get a random event with conversational AI description
- `GET /api/event/category/{category}` - Get a random event from a specific category
- `GET /api/events/all` - Get all events (for testing)

## Configuration

Your Supabase credentials are already configured in `app/core/config.py`:
- **URL**: https://wopjezlgtborpnhcfvoc.supabase.co
- **Key**: (Anon key configured)

## Next Steps

1. Go to your Supabase project: https://wopjezlgtborpnhcfvoc.supabase.co
2. Navigate to the SQL Editor
3. Run the CREATE TABLE SQL above
4. Insert the sample data
5. Test the API endpoints!

