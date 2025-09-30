# 🚀 Deployment Guide for AR Trading API

## Quick Start - Railway (Recommended)

### Step 1: Prepare Your Repository
1. Make sure your code is pushed to GitHub
2. Ensure you have the following files in your repo:
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `src/main.py`

### Step 2: Deploy to Railway
1. Go to [Railway.app](https://railway.app)
2. Sign up with your GitHub account
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect it's a Python app

### Step 3: Add Database
1. In your Railway project dashboard
2. Click "New" → "Database" → "PostgreSQL"
3. Railway will automatically set the `DATABASE_URL` environment variable

### Step 4: Set Environment Variables
In Railway dashboard, go to your app's "Variables" tab and add:
```
DATABASE_URL=postgresql://... (auto-set by Railway)
# Add your exchange API keys if needed
BITGET_API_KEY=your_key
BITGET_API_SECRET=your_secret
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret
```

### Step 5: Deploy
- Railway will automatically deploy when you push to GitHub
- Your app will be available at `https://your-app-name.railway.app`

---

## Alternative: Render (Free Tier)

### Step 1: Prepare Repository
Same as Railway - ensure all files are in your GitHub repo.

### Step 2: Deploy to Render
1. Go to [Render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository

### Step 3: Configure Service
- **Name**: `ar-trading-api`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

### Step 4: Add Database
1. In Render dashboard, click "New" → "PostgreSQL"
2. Note the connection string
3. Add it as `DATABASE_URL` in your web service environment variables

### Step 5: Set Environment Variables
Add the same environment variables as in Railway.

---

## Alternative: Fly.io (Free Tier)

### Step 1: Install Fly CLI
```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Or download from https://fly.io/docs/hands-on/install-flyctl/
```

### Step 2: Login and Create App
```bash
fly auth login
fly launch
```

### Step 3: Configure Database
```bash
fly postgres create
fly postgres attach <your-postgres-app-name>
```

### Step 4: Set Secrets
```bash
fly secrets set DATABASE_URL="postgresql://..."
fly secrets set BITGET_API_KEY="your_key"
fly secrets set BITGET_API_SECRET="your_secret"
```

### Step 5: Deploy
```bash
fly deploy
```

---

## Environment Variables Reference

### Required
- `API_KEY`: Your secret API key for authentication
- `DATABASE_URL`: Database connection string (SQLite for local, PostgreSQL for production)

### Optional (for trading features)
- `BITGET_API_KEY`: Bitget API key
- `BITGET_API_SECRET`: Bitget API secret
- `MEXC_API_KEY`: MEXC API key
- `MEXC_API_SECRET`: MEXC API secret
- `BITUNIX_API_KEY`: Bitunix API key
- `BITUNIX_API_SECRET`: Bitunix API secret

### Telegram Bot (Optional)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID for notifications

---

## SQLite Configuration (Recommended for Low Traffic)

For your use case with minimal database operations, SQLite is perfect:

### Local Development
```bash
# SQLite database will be created automatically
DATABASE_URL=sqlite:///./ar_trade.db
```

### Render Deployment (SQLite)
```bash
# Render supports SQLite out of the box
DATABASE_URL=sqlite:///./ar_trade.db
```

### Advantages of SQLite
- ✅ **No external database needed**
- ✅ **Zero configuration**
- ✅ **Perfect for low traffic**
- ✅ **Automatic backups with your app**
- ✅ **No additional costs**

---

## Telegram Bot Setup

### Step 1: Create Telegram Bot
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow instructions to create your bot
4. Save the bot token

### Step 2: Get Your Chat ID
1. Message your bot: `/start`
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your `chat_id` in the response

### Step 3: Configure Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Step 4: Test Your Bot
```bash
# Send test message
curl -X POST "https://your-app-url/telegram/test" \
  -H "X-API-Key: your_api_key"

# Send market report
curl -X POST "https://your-app-url/telegram/report" \
  -H "X-API-Key: your_api_key"

# Start scheduler (reports every 3 hours)
curl -X POST "https://your-app-url/telegram/scheduler" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"action": "start", "interval_hours": 3}'
```

---

## Testing Your Deployment

1. **Health Check**: Visit `https://your-app-url/health`
2. **API Docs**: Visit `https://your-app-url/docs`
3. **Test Endpoints**: Use the interactive docs to test your API

---

## Cost Comparison

| Platform | Free Tier | Database | Custom Domain | SSL |
|----------|-----------|----------|---------------|-----|
| Railway | $5/month credit | ✅ Included | ✅ | ✅ |
| Render | Free (sleeps after 15min) | ✅ Included | ✅ | ✅ |
| Fly.io | Free (3 shared-cpu-1x) | ✅ Included | ✅ | ✅ |

**Recommendation**: Start with Railway for simplicity, then move to Render if you need more control.

---

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all imports use `src.` prefix
2. **Database Connection**: Verify `DATABASE_URL` is set correctly
3. **Port Issues**: Ensure your app uses `$PORT` environment variable
4. **CORS Errors**: The app is configured to allow all origins for deployment

### Debug Commands

```bash
# Check logs (Railway)
railway logs

# Check logs (Render)
# Available in Render dashboard

# Check logs (Fly.io)
fly logs
```

---

## Next Steps

1. **Domain**: Add a custom domain for easier access
2. **Monitoring**: Set up health checks and monitoring
3. **Backup**: Configure database backups
4. **Scaling**: Upgrade plan if needed (unlikely for your use case)

Your app should now be live and accessible from anywhere! 🎉 