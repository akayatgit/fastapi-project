# Spotive API - Advanced Analytics Features

## 🎯 Overview

The Spotive API now includes comprehensive analytics and logging capabilities designed for:
- 🐛 Real-time debugging
- 📊 Data science analysis
- 📈 Performance monitoring
- 🔍 User behavior insights

## 🚀 Quick Access

### Local Development
- **Analytics Dashboard**: http://127.0.0.1:8000/api/logs/analytics
- **Simple Logs**: http://127.0.0.1:8000/api/logs
- **JSON API**: http://127.0.0.1:8000/api/logs/json

### Production (Vercel)
- **Analytics Dashboard**: https://your-project.vercel.app/api/logs/analytics
- **Simple Logs**: https://your-project.vercel.app/api/logs
- **JSON API**: https://your-project.vercel.app/api/logs/json

## 📊 Features

### 1. Advanced Analytics Dashboard (`/api/logs/analytics`)

#### Powerful Filters
- ⏰ **Time Range**:
  - All Time
  - Past Hour
  - Past 24 Hours
  - Past Week
  - Custom Date Range (picker)

- 🎯 **Endpoint Filter**: 
  - All Endpoints
  - Specific endpoints (auto-populated)

- ✅ **Status Filter**:
  - All
  - Success Only
  - Failed Only

- 📊 **Sorting**:
  - By Timestamp (default)
  - By Duration (find slow requests)
  - By Status (group by success/failure)

- 🔄 **Order**:
  - Descending (newest/slowest first)
  - Ascending (oldest/fastest first)

#### Key Metrics (10 Cards)

**Volume Metrics**:
1. Total Requests
2. Successful Requests
3. Failed Requests
4. Success Rate %

**Performance Metrics**:
5. Average Response Time
6. Min Response Time
7. Max Response Time
8. Median Response Time
9. **P95 Response Time** (95th percentile - SLA monitoring)
10. **P99 Response Time** (99th percentile - outlier detection)

#### Analytics Charts

**📍 Top 10 Endpoints**
- Request distribution by endpoint
- Identify most-used APIs

**🔧 HTTP Methods**
- GET vs POST distribution
- Method usage patterns

**⚠️ Top 10 Errors**
- Error frequency analysis
- Most common failure reasons
- Truncated with hover for full text

**👥 Top 10 Clients**
- Request distribution by IP
- Identify high-volume users

**📋 Detailed Logs Table**
- Top 100 requests
- Full request body
- Error messages
- Color-coded success/failure
- Truncated with hover tooltips

#### Export Capabilities

**📥 CSV Export**
- One-click download
- Respects all filters
- Timestamped filename: `spotive_logs_20251105_103045.csv`
- Perfect for:
  - Excel analysis
  - Pandas DataFrames
  - R statistical analysis
  - Tableau/PowerBI
  - Machine learning

### 2. Simple Logs Dashboard (`/api/logs`)

- Real-time request monitoring
- Full request body display
- Error highlighting
- Clean, simple interface
- No auto-refresh (manual refresh only)

### 3. Supabase Persistent Logs

**Table**: `api_logs`

**Logged Automatically** (async, no performance impact):
- Every call to `/api/event/by-interests`
- Timestamp
- User interests (input)
- Mapped categories (AI output)
- Total matching events
- Selected event details (id, name, category)
- Success/failure status
- Error messages
- Response time (ms)
- Client IP & User Agent

**Benefits**:
- ✅ Survives server restarts
- ✅ Unlimited history (vs 1000 in-memory)
- ✅ SQL query access
- ✅ Data science ready
- ✅ Zero impact on API performance (async)

## 🔍 Use Cases

### For Developers

**Debug Conversational Agent Issues**:
1. Open `/api/logs/analytics`
2. Filter: Past Hour, Failed Only
3. See exactly what the agent sent
4. Compare with working curl request
5. Identify parameter mismatches

**Monitor API Health**:
- Check success rate
- Monitor P95/P99 response times
- Set SLA alerts based on metrics

**Find Performance Bottlenecks**:
- Sort by Duration (descending)
- Identify slow endpoints
- Analyze outliers (P99)

### For Data Scientists

**User Behavior Analysis**:
```sql
-- Query Supabase for popular interests
SELECT 
  interests,
  COUNT(*) as frequency,
  AVG(response_time_ms) as avg_response_time
FROM api_logs
WHERE success = true
GROUP BY interests
ORDER BY frequency DESC
LIMIT 20;
```

**Category Performance**:
```sql
-- Analyze which categories perform best
SELECT 
  selected_event_category,
  COUNT(*) as times_suggested,
  AVG(total_matching_events) as avg_pool_size,
  AVG(response_time_ms) as avg_response_time
FROM api_logs
WHERE success = true
GROUP BY selected_event_category
ORDER BY times_suggested DESC;
```

**Time-based Patterns**:
```sql
-- Requests by hour of day
SELECT 
  EXTRACT(HOUR FROM timestamp) as hour,
  COUNT(*) as requests,
  AVG(response_time_ms) as avg_response_time
FROM api_logs
GROUP BY hour
ORDER BY hour;
```

**Error Analysis**:
```sql
-- Most common errors
SELECT 
  error_message,
  COUNT(*) as occurrences,
  AVG(response_time_ms) as avg_response_time
FROM api_logs
WHERE success = false
GROUP BY error_message
ORDER BY occurrences DESC;
```

**Interest Mapping Analysis**:
```sql
-- See what categories users' interests map to
SELECT 
  mapped_categories->0 as top_category,
  COUNT(*) as frequency
FROM api_logs
WHERE mapped_categories IS NOT NULL
GROUP BY top_category
ORDER BY frequency DESC;
```

### For Product/Business

**Usage Patterns**:
- Peak hours analysis
- Most popular event categories
- User retention (repeat clients)

**Conversion Metrics**:
- Success rate trends
- Drop-off points
- User journey analysis

**ROI Analysis**:
- API cost per request (OpenAI)
- Value delivered (events suggested)
- User satisfaction proxy (low error rate)

## 📥 CSV Export Schema

```csv
timestamp,method,path,status_code,duration_ms,success,client_ip,user_agent,request_body,error
2025-11-05T10:30:45.123456,POST,/api/event/by-interests,200,1250.5,True,192.168.1.1,ElevenLabs/1.0,"{""interests"": ""music, outdoor""}",
```

**Perfect for**:
- Pandas: `df = pd.read_csv('spotive_logs.csv')`
- Excel: Open directly
- R: `data <- read.csv('spotive_logs.csv')`
- Any BI tool

## 🎨 Dashboard Features

### Visual Indicators

- 🟢 **Green rows** = Successful requests
- 🔴 **Red rows** = Failed requests
- 📊 **Color-coded metrics** (success=green, errors=red)
- 📈 **Distribution charts** (endpoints, methods, errors, clients)

### Interactive Elements

- 🔍 **Filter dropdowns** (instant filtering)
- 📅 **Date picker** (custom range)
- 📥 **Export button** (CSV download)
- 🗑️ **Clear logs** button
- 🔄 **Refresh** button (manual, no auto-refresh)

### Responsive Design

- ✅ Grid layout (adapts to screen size)
- ✅ Scrollable tables
- ✅ Truncated long text (hover for full)
- ✅ Modern, clean UI

## 🎯 Key Metrics Explained

### P95 Response Time
**95th percentile** - 95% of requests complete within this time.
- Industry standard for SLA monitoring
- Better than average (not skewed by outliers)
- Example: P95=1500ms means 95% of requests are under 1.5 seconds

### P99 Response Time
**99th percentile** - 99% of requests complete within this time.
- Catches outliers and edge cases
- Critical for user experience
- Example: P99=3000ms means only 1% of requests take over 3 seconds

### Success Rate
**Percentage of successful requests**
- Target: >99% for production
- Monitor trends over time
- Alert if drops below threshold

### Median vs Average
- **Median**: Middle value (not affected by outliers)
- **Average**: Mean (can be skewed by outliers)
- If median << average → Some very slow requests

## 🔧 Setup Instructions

### Step 1: Create Supabase Table

Go to Supabase SQL Editor and run:

```sql
-- Copy from SUPABASE_SETUP.md or API_LOGS_SCHEMA.sql
CREATE TABLE api_logs (
  id bigserial PRIMARY KEY,
  timestamp timestamp with time zone NOT NULL,
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
  user_agent text
);
```

### Step 2: Deploy Code

```bash
git add .
git commit -m "Add advanced analytics dashboard"
git push
```

### Step 3: Access Dashboard

Visit: `https://your-project.vercel.app/api/logs/analytics`

## 📱 Integration Flow

```
User/Agent calls API
    ↓
Middleware logs to memory
    ↓
API processes request
    ↓
Response generated
    ↓
Background task logs to Supabase (async)
    ↓
Response sent to user (no waiting!)
    ↓
View analytics at /api/logs/analytics
```

## 💡 Pro Tips

### Finding Issues

**Scenario**: Conversational agent not working
1. Open `/api/logs/analytics`
2. Filter: Past Hour, `/api/event/by-interests`, Failed Only
3. See request body from agent
4. Compare with working curl request
5. Spot the difference!

### Performance Monitoring

**Check SLA compliance**:
- Set target: P95 < 2000ms
- Monitor: Visit analytics daily
- Alert: If P95 > 2000ms, investigate slow requests

### Data Analysis

**Export and analyze**:
```python
import pandas as pd

# Load exported CSV
df = pd.read_csv('spotive_logs_20251105_103045.csv')

# Analyze
print(df['success'].value_counts())
print(df['duration_ms'].describe())
print(df['request_body'].value_counts().head(10))
```

## 🆕 What's New vs Old Logs Page

| Feature | Old `/api/logs` | New `/api/logs/analytics` |
|---------|-----------------|---------------------------|
| Filtering | ❌ No | ✅ Advanced (5 filters) |
| Metrics | Basic (4) | **Advanced (10)** |
| Percentiles | ❌ No | ✅ P95, P99 |
| Sorting | ❌ No | ✅ Multiple options |
| Export | ❌ No | ✅ CSV download |
| Charts | ❌ No | ✅ 4 distribution charts |
| Auto-refresh | ❌ Removed | ❌ Removed |
| Date range | ❌ No | ✅ Custom picker |

## 🎓 Data Science Queries

See `API_LOGGING_GUIDE.md` for more SQL examples!

## 🔐 Security Note

The analytics page is currently public. For production:
- Add authentication
- Restrict to admin users only
- Use Supabase RLS (Row Level Security)
- Consider IP whitelisting

## 📋 Checklist

To fully enable analytics:

- [ ] Create `api_logs` table in Supabase (run SQL)
- [ ] Deploy code to Vercel
- [ ] Make some API calls
- [ ] Visit `/api/logs/analytics`
- [ ] Test filters
- [ ] Export CSV
- [ ] Run SQL queries on Supabase
- [ ] Set up monitoring alerts (future)

---

**Your analytics dashboard is ready for production! 🎉**

