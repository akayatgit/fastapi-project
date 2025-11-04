# Deploying Spotive API to Vercel

## 🚨 Important: Vercel Uses OpenAI, Not Ollama

Vercel is a **serverless platform** and doesn't support running Ollama (which requires a local server). The API automatically switches to **OpenAI** when deployed to Vercel.

## Prerequisites

1. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
2. **OpenAI API Key** - Get one from [platform.openai.com](https://platform.openai.com)
3. **Supabase Database** - Already set up ✅

## Step-by-Step Deployment

### 1. Install Vercel CLI (Optional)

```bash
npm install -g vercel
```

### 2. Set Up Environment Variables in Vercel

Go to your Vercel project settings and add these environment variables:

| Variable Name | Value | Required |
|--------------|-------|----------|
| `SUPABASE_URL` | `https://wopjezlgtborpnhcfvoc.supabase.co` | ✅ Yes |
| `SUPABASE_KEY` | Your Supabase anon key | ✅ Yes |
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `LLM_PROVIDER` | `openai` | ✅ Yes |
| `LLM_MODEL` | `gpt-3.5-turbo` | Optional (auto-set) |
| `PRODUCTION` | `true` | Optional |

### 3. Deploy via Vercel Dashboard

**Option A: Deploy from GitHub**

1. Push your code to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your repository
4. Vercel will auto-detect it as a Python project
5. Add environment variables in the settings
6. Click "Deploy"

**Option B: Deploy via CLI**

```bash
# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### 4. Add Environment Variables via CLI

```bash
vercel env add SUPABASE_URL
# Paste: https://wopjezlgtborpnhcfvoc.supabase.co

vercel env add SUPABASE_KEY
# Paste your Supabase key

vercel env add OPENAI_API_KEY
# Paste your OpenAI API key

vercel env add LLM_PROVIDER
# Type: openai
```

### 5. Verify Deployment

Once deployed, visit your Vercel URL:

```bash
curl https://your-project.vercel.app/
```

You should see:

```json
{
  "message": "Welcome to Spotive API!",
  "status": "active",
  "environment": {
    "is_vercel": true,
    "is_production": true,
    "llm_provider": "openai",
    "llm_model": "gpt-3.5-turbo",
    "llm_available": true
  }
}
```

## Environment Variable Configuration

### In Vercel Dashboard

1. Go to your project → **Settings** → **Environment Variables**
2. Add each variable:
   - **SUPABASE_URL**: `https://wopjezlgtborpnhcfvoc.supabase.co`
   - **SUPABASE_KEY**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (your full key)
   - **OPENAI_API_KEY**: `sk-...` (your OpenAI key)
   - **LLM_PROVIDER**: `openai`
   - **LLM_MODEL**: `gpt-3.5-turbo` (or `gpt-4` if you have access)

3. **Important**: Set these for **Production**, **Preview**, and **Development** environments

### Using Vercel Secrets (More Secure)

```bash
# Add secrets
vercel secrets add supabase_url "https://wopjezlgtborpnhcfvoc.supabase.co"
vercel secrets add supabase_key "your-supabase-key"
vercel secrets add openai_api_key "your-openai-key"

# These are then referenced in vercel.json
```

## Troubleshooting

### Error: "Connection refused" / "[Errno 111]"

**Problem**: The API is trying to connect to Ollama, which doesn't exist on Vercel.

**Solution**: Make sure `OPENAI_API_KEY` environment variable is set in Vercel.

**Fix Steps**:
1. Go to Vercel Dashboard → Settings → Environment Variables
2. Add `OPENAI_API_KEY` with your OpenAI key
3. Redeploy: `vercel --prod` or trigger a new deployment

### Error: "OPENAI_API_KEY is required"

**Problem**: The OpenAI API key is missing.

**Solution**: Add it to Vercel environment variables.

### Error: "No events found in database"

**Problem**: Supabase database is empty or connection failed.

**Solution**:
1. Check Supabase credentials are correct
2. Make sure you've created the `events` table (see SUPABASE_SETUP.md)
3. Insert sample events

### Error: "Module not found"

**Problem**: Missing dependencies.

**Solution**: Make sure `requirements.txt` is in the root directory and contains all dependencies.

### LLM responses are slow

**Problem**: OpenAI API calls take time.

**Solution**:
- Use `gpt-3.5-turbo` instead of `gpt-4` (faster and cheaper)
- Consider caching responses for common queries
- Implement async calls if needed

## Cost Considerations

### OpenAI API Pricing (as of 2024)

**GPT-3.5-Turbo**:
- Input: $0.0005 / 1K tokens
- Output: $0.0015 / 1K tokens
- ~20-word response ≈ 30 tokens ≈ $0.000045 per request

**GPT-4**:
- Input: $0.03 / 1K tokens
- Output: $0.06 / 1K tokens
- More expensive but higher quality

### Estimated Costs

For **1000 API calls** using GPT-3.5-Turbo:
- Cost: ~$0.05 - $0.10
- Very affordable for MVP!

## Performance Optimization

### 1. Use Lightweight Model

Set `LLM_MODEL=gpt-3.5-turbo` (fast, cheap) instead of `gpt-4`

### 2. Enable Caching (Future)

Cache LLM responses for frequently requested events.

### 3. Reduce Token Usage

Keep prompts concise to reduce tokens.

### 4. Async Processing (Future)

For multiple events, process in parallel.

## Vercel Configuration Files

### `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### `.vercelignore` (Optional)

```
__pycache__/
*.pyc
.env
.env.local
venv/
*.log
.pytest_cache/
```

## Testing Deployment

### Test All Endpoints

```bash
# Set your Vercel URL
VERCEL_URL="https://your-project.vercel.app"

# Health check
curl $VERCEL_URL/

# Random event
curl $VERCEL_URL/api/random-event

# Events by category
curl $VERCEL_URL/api/event/category/concert

# Events by preferences
curl -X POST $VERCEL_URL/api/events/by-preferences \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-11-15", "preferences": "music, outdoor"}'
```

## Monitoring

### Vercel Analytics

1. Enable Analytics in Vercel Dashboard
2. Monitor:
   - Request count
   - Response times
   - Error rates
   - Bandwidth usage

### OpenAI Usage

1. Go to [platform.openai.com/usage](https://platform.openai.com/usage)
2. Monitor API usage and costs

## Auto-Deployment

### With GitHub Integration

Vercel automatically deploys when you:
- Push to `main` branch → Production
- Push to other branches → Preview deployments

### Disable Auto-Deploy

In Vercel Dashboard → Settings → Git → Uncheck "Auto-deploy"

## Domain Configuration

### Add Custom Domain

1. Vercel Dashboard → Settings → Domains
2. Add your domain: `api.spotive.com`
3. Update DNS records as instructed
4. SSL certificate auto-configured ✅

## Environment-Specific Behavior

| Environment | LLM Provider | Model | Behavior |
|-------------|-------------|-------|----------|
| **Local** | Ollama | gemma3 | Free, requires local Ollama server |
| **Vercel** | OpenAI | gpt-3.5-turbo | Paid, automatically switches |
| **Production** | OpenAI | gpt-3.5-turbo | Same as Vercel |

## Next Steps

After deployment:

1. ✅ Test all endpoints
2. ✅ Verify OpenAI integration works
3. ✅ Check Supabase connection
4. 🔄 Integrate with ElevenLabs frontend
5. 🔄 Add Twilio phone integration
6. 🔄 Set up monitoring alerts

## Support

If you encounter issues:

1. Check Vercel deployment logs
2. Verify environment variables are set
3. Test locally first with OpenAI: `LLM_PROVIDER=openai`
4. Check OpenAI API key is valid

---

**Important**: Don't forget to add `OPENAI_API_KEY` to Vercel environment variables! This is the most common issue.

