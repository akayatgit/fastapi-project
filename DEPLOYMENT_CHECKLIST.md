# Spotive API - Vercel Deployment Checklist

## 📋 Pre-Deployment Checklist

### 1. Code Preparation
- [x] Code pushed to GitHub repository
- [x] `requirements.txt` includes all dependencies
- [x] `vercel.json` configuration file created
- [x] `.vercelignore` file created
- [x] Error handling added for LLM unavailability
- [x] Auto-detection of Vercel environment added

### 2. Dependencies
- [x] `langchain-openai` added to requirements.txt
- [x] All packages compatible with Vercel
- [x] No local-only dependencies (Ollama only for local dev)

### 3. Environment Variables Prepared
Gather these values before deployment:

- [ ] **SUPABASE_URL**: `https://wopjezlgtborpnhcfvoc.supabase.co`
- [ ] **SUPABASE_KEY**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (your full key)
- [ ] **OPENAI_API_KEY**: `sk-...` (**REQUIRED** - Get from [platform.openai.com](https://platform.openai.com))
- [ ] **LLM_PROVIDER**: `openai`
- [ ] **LLM_MODEL**: `gpt-3.5-turbo`

### 4. Supabase Database
- [ ] Events table created in Supabase
- [ ] Sample events inserted
- [ ] Test query works: `SELECT * FROM events;`
- [ ] Supabase API accessible from external sources

### 5. OpenAI Account
- [ ] OpenAI account created
- [ ] API key generated
- [ ] Usage limits checked (free tier has limits)
- [ ] Billing set up if needed

---

## 🚀 Deployment Steps

### Step 1: Create Vercel Project
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Vercel auto-detects it as Python project

### Step 2: Configure Environment Variables
In Vercel Dashboard → Settings → Environment Variables:

```
SUPABASE_URL = https://wopjezlgtborpnhcfvoc.supabase.co
SUPABASE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY = sk-...
LLM_PROVIDER = openai
LLM_MODEL = gpt-3.5-turbo
```

**Important**: Add these for ALL environments (Production, Preview, Development)

### Step 3: Deploy
Click "Deploy" button in Vercel

### Step 4: Wait for Build
Monitor build logs for any errors

---

## ✅ Post-Deployment Verification

### 1. Test Health Endpoint
```bash
curl https://your-project.vercel.app/
```

**Expected Response**:
```json
{
  "message": "Welcome to Spotive API!",
  "status": "active",
  "environment": {
    "is_vercel": true,
    "is_production": true,
    "llm_provider": "openai",
    "llm_model": "gpt-3.5-turbo",
    "llm_available": true  ← Should be true!
  }
}
```

### 2. Test Random Event
```bash
curl https://your-project.vercel.app/api/random-event
```

**Check**:
- [ ] Returns event data
- [ ] `"ai_generated": true` in response
- [ ] `suggestion` field contains AI-generated text
- [ ] No connection errors

### 3. Test Category Endpoint
```bash
curl https://your-project.vercel.app/api/event/category/concert
```

### 4. Test MCP Endpoint
```bash
curl -X POST https://your-project.vercel.app/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, outdoor"}'
```

**Check**:
- [ ] Returns matched events
- [ ] Top 3 results have AI suggestions
- [ ] `"source": "Supabase + MCP Filtering"`

### 5. Check All Events
```bash
curl https://your-project.vercel.app/api/events/all
```

**Check**:
- [ ] Returns all events from Supabase
- [ ] Event count matches database

---

## 🐛 Common Issues & Solutions

### Issue 1: "Connection refused" / "[Errno 111]"
**Cause**: Trying to connect to Ollama (not available on Vercel)

**Solution**:
1. Add `OPENAI_API_KEY` to Vercel environment variables
2. Set `LLM_PROVIDER=openai`
3. Redeploy

### Issue 2: "OPENAI_API_KEY is required"
**Cause**: OpenAI key not set

**Solution**:
1. Go to Vercel Settings → Environment Variables
2. Add `OPENAI_API_KEY` with your key from OpenAI
3. Redeploy

### Issue 3: "No events found in database"
**Cause**: Supabase database empty

**Solution**:
1. Go to Supabase SQL Editor
2. Run SQL from `SUPABASE_SETUP.md`
3. Insert sample events
4. Test API again

### Issue 4: "Import langchain_openai could not be resolved"
**Cause**: Warning in VS Code (not an actual error)

**Solution**: Ignore - it's imported dynamically. Works in production.

### Issue 5: Build fails on Vercel
**Cause**: Missing dependencies or Python version

**Solution**:
1. Check `requirements.txt` has all packages
2. Add `runtime.txt` with: `python-3.11`
3. Commit and redeploy

### Issue 6: Slow responses
**Cause**: OpenAI API latency

**Solution**:
- Use `gpt-3.5-turbo` (faster than gpt-4)
- Responses typically take 2-5 seconds
- Consider caching for future optimization

---

## 📊 Monitoring

### After Deployment

**Vercel Dashboard**:
- [ ] Check deployment status (should be "Ready")
- [ ] Monitor function logs for errors
- [ ] Check analytics for request counts

**OpenAI Dashboard**:
- [ ] Go to [platform.openai.com/usage](https://platform.openai.com/usage)
- [ ] Monitor API usage
- [ ] Check costs (should be very low initially)

**Supabase Dashboard**:
- [ ] Monitor database queries
- [ ] Check connection health
- [ ] Verify API usage

---

## 🎯 Success Criteria

Your deployment is successful when:

- [x] Health endpoint returns `"llm_available": true`
- [x] All 5 API endpoints return successful responses
- [x] AI-generated suggestions are natural and conversational
- [x] No "Connection refused" errors
- [x] OpenAI API calls working
- [x] Supabase events retrieved successfully

---

## 📱 Next Steps After Deployment

1. **Save Your Vercel URL**
   - Example: `https://spotive-api.vercel.app`
   - Share with ElevenLabs integration team

2. **Update CORS Settings** (if needed)
   - Add allowed origins for Next.js app
   - Configure in `app/main.py`

3. **Set Up Custom Domain** (optional)
   - Go to Vercel → Settings → Domains
   - Add `api.spotive.com` or similar

4. **Integrate with ElevenLabs**
   - Use Vercel URL in Next.js app
   - Test phone call flow
   - Test WhatsApp integration

5. **Monitor Costs**
   - Track OpenAI usage
   - Set up billing alerts
   - Optimize if needed

6. **Add User Tracking** (future)
   - Store user preferences
   - Track conversation history
   - Improve recommendations

---

## 💰 Cost Estimation

### For MVP (First Month)

**OpenAI API (GPT-3.5-Turbo)**:
- 1000 requests/month: ~$0.05-$0.10
- 10,000 requests/month: ~$0.50-$1.00
- Very affordable! 💸

**Vercel**:
- Free tier: Up to 100GB bandwidth
- Likely stays free for MVP

**Supabase**:
- Free tier: 500MB database
- Plenty for MVP!

**Total MVP Cost**: ~$0-$2/month 🎉

---

## 🔐 Security Checklist

- [ ] API keys stored in Vercel environment variables (not in code)
- [ ] `.env` file in `.gitignore`
- [ ] Supabase Row Level Security configured (future)
- [ ] Rate limiting considered (future)
- [ ] CORS configured properly (when integrating frontend)

---

## 📞 Support

If stuck:
1. Check Vercel build logs
2. Review `VERCEL_DEPLOYMENT.md` troubleshooting section
3. Test locally with `LLM_PROVIDER=openai` first
4. Verify all environment variables are set

---

**Remember**: The main difference between local and Vercel is:
- **Local**: Uses Ollama (free, requires installation)
- **Vercel**: Uses OpenAI (paid, works automatically)

The code automatically switches based on environment! 🚀

