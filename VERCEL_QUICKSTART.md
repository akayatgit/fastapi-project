# Vercel Deployment - Quick Start

## 🚨 The Issue You Had

**Error**: `"Connection refused [Errno 111]"`

**Cause**: Vercel tried to use Ollama (local LLM), which doesn't work on serverless platforms.

**Fix**: ✅ Code now auto-switches to OpenAI on Vercel!

---

## ⚡ Quick Fix (3 Steps)

### 1. Get OpenAI API Key

Go to [platform.openai.com](https://platform.openai.com) → Create API Key

Copy the key (starts with `sk-...`)

### 2. Add to Vercel

**Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**

Add these:

```
OPENAI_API_KEY = sk-your-key-here
LLM_PROVIDER = openai
LLM_MODEL = gpt-3.5-turbo
SUPABASE_URL = https://wopjezlgtborpnhcfvoc.supabase.co
SUPABASE_KEY = your-supabase-key
```

### 3. Redeploy

Push code to GitHub (auto-deploys) OR run:
```bash
vercel --prod
```

---

## ✅ Verify It Works

```bash
curl https://your-project.vercel.app/
```

**Look for:**
```json
{
  "environment": {
    "is_vercel": true,
    "llm_provider": "openai",
    "llm_available": true  ← Must be TRUE!
  }
}
```

---

## 💰 Cost

**Very cheap for MVP!**
- GPT-3.5-Turbo: ~$0.0001 per request
- 1,000 requests: $0.05-$0.10
- 10,000 requests: $0.50-$1.00

---

## 🎯 What Changed

| Before (Local) | After (Vercel) |
|---------------|----------------|
| Ollama | OpenAI |
| gemma3 | gpt-3.5-turbo |
| Free | ~$0.0001/request |
| Local server | Cloud API |

**The code automatically detects Vercel and switches!**

---

## 📚 Full Documentation

- **VERCEL_FIX_SUMMARY.md** - Detailed explanation
- **VERCEL_DEPLOYMENT.md** - Complete guide
- **DEPLOYMENT_CHECKLIST.md** - Step-by-step

---

## 🐛 Still Not Working?

**Double-check:**
1. OpenAI API key is correct
2. All env vars added to Vercel
3. Set for ALL environments (Production + Preview + Development)
4. Redeployed after adding env vars

**Test locally with OpenAI first:**
```bash
export OPENAI_API_KEY="sk-..."
export LLM_PROVIDER="openai"
uvicorn app.main:app --reload
```

---

## ✨ You're Done!

Your API is now production-ready on Vercel! 🚀

Next: Integrate with ElevenLabs and start making calls!

