# Supabase Database Setup for User Profiles

This document contains the SQL commands to create the required tables for the User Profiles & Preferences feature.

## Prerequisites

- Access to your Supabase project dashboard
- Go to: **SQL Editor** in your Supabase dashboard

---

## Table 1: `users`

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
