# Environment Variables for Tribute Integration

Add these environment variables to your deployment configuration:

```bash
# Tribute.tg API Configuration
TRIBUTE_API=your_tribute_api_key_here
TRIBUTE_WEBHOOK_SECRET=your_webhook_secret_here

# Existing variables (keep these)
BOT_TOKEN=your_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Optional: Frontend URL for WebApp
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
```

## How to get Tribute API Key:

1. Go to https://tribute.tg
2. Open Author Panel
3. Click three dots (⋯) → Settings
4. Go to "API Keys" section
5. Click "Generate API Key"
6. Copy and save the key securely

## Webhook Secret:

1. In Tribute.tg Dashboard → Settings → Webhooks
2. Add webhook URL: `https://your-backend-domain.com/billing/tribute/webhook`
3. Select events: "Digital Product Purchase"
4. Generate and save webhook secret
