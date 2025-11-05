# API Logging & Analytics Guide

## Overview

The Spotive API now includes comprehensive logging for debugging and data analysis:
1. **In-Memory Logs** - For real-time debugging (last 1000 requests)
2. **Supabase Logs** - For long-term analytics and data analysis

## Features

### 1. Real-Time Audit Logs (In-Memory)

**Endpoint**: `GET /api/logs`

Displays a beautiful HTML dashboard with:
- 📊 Statistics (Total requests, Success rate, Failed requests, Avg response time)
- 📝 List of all API calls (newest first)
- 🎨 Color-coded by success/failure
- 🔄 Auto-refreshes every 5 seconds
- 🎯 Shows full request body for debugging
- ⚠️ Highlights errors with detailed error messages

**Use Cases**:
- Debug conversational agent integration issues
- See exactly what parameters the agent is sending
- Compare working curl requests with failing agent requests
- Monitor API health in real-time

### 2. Supabase Analytics Logs (Persistent)

**Table**: `api_logs`

Automatically logs every call to `/api/event/by-interests` with:
- Timestamp
- User interests (input)
- Mapped categories (what the AI chose)
- Total matching events
- Selected event details
- Success/failure status
- Error messages (if any)
- Response time
- Client IP & User Agent

**Use Cases**:
- Analyze user behavior patterns
- Understand popular interests/categories
- Track API performance over time
- Identify common errors
- Data science & machine learning
- Business intelligence reporting

## Setup

### Step 1: Create Supabase Table

Run the SQL in `API_LOGS_SCHEMA.sql`:

```sql
-- Go to Supabase Dashboard → SQL Editor
-- Paste and run the SQL from API_LOGS_SCHEMA.sql
```

### Step 2: Deploy Your Code

```bash
git add .
git commit -m "Add comprehensive API logging"
git push
```

Vercel will auto-deploy.

### Step 3: Access the Logs

**Real-Time Dashboard**:
```
https://your-project.vercel.app/api/logs
```

**JSON API**:
```
https://your-project.vercel.app/api/logs/json
```

**Supabase Table**:
- Go to Supabase Dashboard
- Navigate to Table Editor
- Open `api_logs` table
- View all historical logs

## API Endpoints

### 1. View Logs (HTML)
```
GET /api/logs
```
Returns beautiful HTML dashboard with real-time logs.

### 2. Get Logs (JSON)
```
GET /api/logs/json
```
Returns logs as JSON for programmatic access.

**Response**:
```json
{
  "total_logs": 150,
  "logs": [...]
}
```

### 3. Clear Logs
```
GET /api/logs/clear
```
Clears all in-memory logs (doesn't affect Supabase logs).

## How It Works

### Request Flow

```
1. User/Agent calls API
   ↓
2. Request logged to memory (middleware)
   ↓
3. API processes request
   ↓
4. Response generated
   ↓
5. Log sent to Supabase (async, non-blocking)
   ↓
6. Response returned to user
```

### Background Logging

Supabase logging runs **asynchronously** using FastAPI's `BackgroundTasks`:
- ✅ Doesn't slow down API response
- ✅ Runs after response is sent
- ✅ Fails silently if Supabase is down
- ✅ No impact on user experience

## Data Analysis Examples

### Example 1: Most Popular Interests

```sql
SELECT 
  interests,
  COUNT(*) as request_count
FROM api_logs
WHERE success = true
GROUP BY interests
ORDER BY request_count DESC
LIMIT 10;
```

### Example 2: Success Rate by Interest Category

```sql
SELECT 
  mapped_categories->>0 as top_category,
  COUNT(*) as total,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM api_logs
WHERE mapped_categories IS NOT NULL
GROUP BY top_category
ORDER BY total DESC;
```

### Example 3: Average Response Time by Hour

```sql
SELECT 
  EXTRACT(HOUR FROM timestamp) as hour,
  AVG(response_time_ms) as avg_response_time,
  COUNT(*) as requests
FROM api_logs
GROUP BY hour
ORDER BY hour;
```

### Example 4: Most Suggested Events

```sql
SELECT 
  selected_event_name,
  selected_event_category,
  COUNT(*) as times_suggested
FROM api_logs
WHERE success = true
GROUP BY selected_event_name, selected_event_category
ORDER BY times_suggested DESC
LIMIT 20;
```

### Example 5: Error Analysis

```sql
SELECT 
  error_message,
  COUNT(*) as occurrences,
  AVG(response_time_ms) as avg_response_time
FROM api_logs
WHERE success = false
GROUP BY error_message
ORDER BY occurrences DESC;
```

## Troubleshooting

### Issue: Logs page shows error

**Solution**: Access `/api/logs/json` instead to see raw logs, or check browser console.

### Issue: Logs not appearing in Supabase

**Possible causes**:
1. Table not created - Run SQL schema
2. Wrong table name - Must be exactly `api_logs`
3. Supabase credentials wrong - Check `.env`
4. Network issue - Check Vercel logs

**Check**:
```bash
# View Vercel logs
vercel logs
```

### Issue: Logs filling up quickly

**Solution**: Logs are capped at 1000 entries in memory. For Supabase, set up automatic cleanup:

```sql
-- Delete logs older than 90 days
DELETE FROM api_logs 
WHERE timestamp < NOW() - INTERVAL '90 days';
```

Or create a Postgres function to run daily.

## Debugging with Logs

### Scenario: Conversational Agent Not Working

1. **Open logs page**: `https://your-api.vercel.app/api/logs`
2. **Make test call with curl** (working):
```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "music, outdoor"}'
```
3. **Make call from agent** (not working)
4. **Compare the two log entries**:
   - Check Request Body
   - Compare parameter names
   - Check data types
   - Look for missing fields
5. **Identify the difference**
6. **Fix agent configuration**

### Common Issues Found

| Issue | What You'll See | Solution |
|-------|----------------|----------|
| Wrong parameter name | `"interest"` instead of `"interests"` | Update agent config |
| Wrong data type | Array instead of string | Change to comma-separated string |
| Missing body | `request_body: null` | Agent not sending body |
| Wrong endpoint | Path shows wrong URL | Update agent endpoint |
| Malformed JSON | `request_body_error` in logs | Fix JSON syntax in agent |

## Performance Impact

**In-Memory Logs**:
- Minimal impact (~0.1ms per request)
- Capped at 1000 entries
- Cleared on restart

**Supabase Logs**:
- **Zero impact** on response time (async)
- Runs in background
- Fails gracefully if Supabase down

## Security Considerations

**What's Logged**:
- ✅ Interests (safe to log)
- ✅ Categories (safe)
- ✅ Event IDs (safe)
- ✅ Response times (safe)
- ✅ Errors (safe)

**What's NOT Logged**:
- ❌ Authentication tokens
- ❌ API keys
- ❌ Passwords
- ❌ Personal user data
- ❌ Credit card info

**Access Control**:
- Logs page is public (contains no sensitive data)
- Supabase table should have RLS (Row Level Security) enabled
- Consider adding authentication for production

## Next Steps

1. ✅ Deploy code to Vercel
2. ✅ Create `api_logs` table in Supabase
3. ✅ Make test API calls
4. ✅ View logs at `/api/logs`
5. ✅ Check Supabase table for persistent logs
6. ✅ Set up data analysis queries
7. 🔄 Monitor and optimize based on insights

---

**Happy Debugging!** 🔍📊

