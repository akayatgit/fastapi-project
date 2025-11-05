# Testing the Category Mapping Bug Fix

## 🐛 Original Bug

**What Happened**:
- User interest: "comedy"
- LLM returned: ALL 8 categories
- Query result: Events from ALL categories
- Random pick: ISKCON (spiritual) ❌ WRONG!

## ✅ Expected After Fix

**What Should Happen**:
- User interest: "comedy"
- LLM returns: `["comedy"]` OR fallback to `["comedy"]`
- Query result: ONLY comedy events
- Random pick: Standup Comedy Night ✅ CORRECT!

## 🧪 Test Cases

### Test 1: Comedy Interest (The Bug Case)

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy"}'
```

**Expected Response**:
```json
{
  "success": true,
  "interests": "comedy",
  "mapped_categories": ["comedy"],  // ✅ ONLY comedy!
  "mapping_method": "llm",          // or "keyword_fallback"
  "total_matching_events": 1,
  "event_details": {
    "name": "Standup Comedy Night",  // ✅ COMEDY EVENT!
    "category": "comedy"
  }
}
```

**Red Flags** (if you see these, there's still an issue):
```json
{
  "mapped_categories": ["concert", "sports", "outdoor", ...],  // ❌ BAD - too many!
  "event_details": {
    "category": "spiritual"  // ❌ BAD - wrong category!
  }
}
```

### Test 2: Music Interest

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "music"}'
```

**Expected**:
```json
{
  "mapped_categories": ["concert"],
  "event_details": {
    "category": "concert"
  }
}
```

### Test 3: Multiple Interests

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy, music"}'
```

**Expected**:
```json
{
  "mapped_categories": ["comedy", "concert"],  // ✅ 2 categories (both relevant)
  "event_details": {
    "category": "comedy" or "concert"  // ✅ One of the two
  }
}
```

### Test 4: Spiritual Interest

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "spiritual, meditation"}'
```

**Expected**:
```json
{
  "mapped_categories": ["spiritual"],
  "event_details": {
    "name": "Iskcon Janmashtami Celebration",
    "category": "spiritual"
  }
}
```

### Test 5: Broad Interest (Edge Case)

```bash
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "fun, entertainment"}'
```

**Expected**:
```json
{
  "mapped_categories": ["entertainment"],  // ✅ Max 3 categories
  "mapping_method": "llm"
}
```

## 📊 Check Vercel Logs

### Step 1: Start Logs Stream

```bash
vercel logs --follow
```

### Step 2: Make API Call

Run one of the test cases above.

### Step 3: Look for DEBUG Output

**Good Output** (LLM working):
```
DEBUG - LLM raw response for 'comedy': ["comedy"]
DEBUG - Parsed categories: ['comedy']
DEBUG - After validation: ['comedy'] (filtered from 1)
```

**Fallback Triggered** (LLM failed, but fixed):
```
DEBUG - LLM raw response for 'comedy': ["concert", "sports", "outdoor", ...]
DEBUG - Parsed categories: ['concert', 'sports', 'outdoor', ...]
DEBUG - After validation: [...] (filtered from 8)
DEBUG - LLM returned invalid categories (8), using keyword matching fallback
DEBUG - Keyword matching result: ['comedy']
```

## 🎯 What to Monitor

### In API Response

**Field**: `mapping_method`

| Value | Meaning | Action Needed |
|-------|---------|---------------|
| `"llm"` | ✅ LLM worked correctly | None - all good! |
| `"keyword_fallback"` | ⚠️ LLM failed, fallback used | Monitor frequency |
| `"error"` | ❌ Both methods failed | Investigate logs |

**Ideal**: >80% should be `"llm"`

**If** `"keyword_fallback"` > 50%:
- LLM prompt needs more tuning
- Consider model upgrade (gpt-4)
- Check OpenAI API status

### In Supabase Analytics

Query to check mapping method distribution:

```sql
SELECT 
  mapping_method,
  COUNT(*) as usage_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM api_logs
WHERE success = true
GROUP BY mapping_method
ORDER BY usage_count DESC;
```

**Target**:
```
mapping_method | usage_count | percentage
---------------|-------------|------------
llm            | 850         | 85.00
keyword_fallback | 150       | 15.00
```

## 🔍 Analytics Dashboard Check

Visit: `/api/logs/analytics`

**Filter**: 
- Time: Past Hour
- Endpoint: `/api/event/by-interests`
- Status: All

**Look for**:
- Request body shows `{"interests": "comedy"}`
- Success rate should be high (>90%)
- No errors related to category mapping

## ✅ Success Criteria

The fix is successful if:

1. ✅ "comedy" interest returns comedy events (not spiritual/other)
2. ✅ `mapped_categories` has 1-3 items (not 8)
3. ✅ `mapping_method` present in response
4. ✅ DEBUG logs show correct category counts
5. ✅ Keyword fallback works when LLM fails
6. ✅ No "[Errno 111] Connection refused" errors
7. ✅ Analytics dashboard loads without errors

## 🚨 If Tests Fail

### Scenario 1: Still Getting Wrong Categories

**Symptoms**: "comedy" returns all 8 categories

**Debug Steps**:
1. Check Vercel logs for DEBUG output
2. See what LLM is returning
3. Check if `mapping_method` is "keyword_fallback"
4. If keyword_fallback, check the result
5. If still wrong, keywords may need updating

**Fix**:
Update keyword map in `app/main.py` around line 163

### Scenario 2: "keyword_fallback" Used Too Often

**Symptoms**: >50% of requests use fallback

**Possible Causes**:
1. LLM model not following instructions (try gpt-4)
2. Prompt needs improvement
3. OpenAI API issues

**Fix Options**:
1. Switch to `LLM_MODEL=gpt-4` (more reliable, bit slower/expensive)
2. Simplify prompt further
3. Increase temperature to 0.5 (more focused)

### Scenario 3: No Results Found

**Symptoms**: 404 error, "No events found"

**Debug**:
1. Check what categories were mapped
2. Verify those categories exist in database
3. Check if `mapping_method` shows which was used

**Fix**:
Ensure database has events for all 9 categories

## 📋 Pre-Deployment Checklist

Before deploying the fix:

- [x] Updated LLM prompt with strict rules
- [x] Added validation (reject if >4 categories)
- [x] Implemented keyword fallback
- [x] Added DEBUG logging
- [x] Added `mapping_method` to response
- [x] Updated Supabase schema
- [x] Updated documentation
- [x] Added "comedy" to valid_categories
- [x] Removed auto-refresh from pages

## 🚀 Deployment Steps

```bash
# 1. Update Supabase table (if not already created)
# Go to Supabase SQL Editor and run the SQL from SUPABASE_SETUP.md

# 2. Deploy to Vercel
git add .
git commit -m "Fix: Category mapping bug - comedy now returns comedy events"
git push

# 3. Wait for deployment

# 4. Test immediately
curl -X POST https://your-project.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy"}'

# 5. Check Vercel logs
vercel logs

# 6. Verify mapping_method
# Should be "llm" or "keyword_fallback", event should be comedy
```

## 📞 Quick Smoke Test

After deployment, run this:

```bash
# Test 1
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "comedy"}'

# Verify: Should get comedy event, not spiritual!

# Test 2  
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "music"}'

# Verify: Should get concert event

# Test 3
curl -X POST https://your-api.vercel.app/api/event/by-interests \
  -H "Content-Type: application/json" \
  -d '{"interests": "outdoor"}'

# Verify: Should get outdoor event
```

**All 3 pass** = Bug is fixed! ✅

## 📊 Monitor Post-Deployment

### First Hour
- Check Vercel logs every 10 minutes
- Look for DEBUG outputs
- Monitor `mapping_method` distribution
- Check error rate

### First Day
- Query Supabase api_logs table
- Check mapping_method stats
- Verify success rate >95%
- Check if any unexpected errors

### First Week
- Analyze which method performs better
- Check LLM accuracy trends
- Optimize prompt if needed
- Consider model upgrade if fallback >30%

---

**The bug is now architecturally fixed with multiple safety layers!** 🎉

