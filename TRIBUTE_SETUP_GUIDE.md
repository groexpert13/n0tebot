# Tribute.tg Integration Setup Guide

## Overview

This guide walks you through setting up Tribute.tg payment integration for your n0te bot with the following products:

- **Monthly Subscription**: €2.99/month
- **Yearly Subscription**: €29/year (19% discount)
- **Audio Minutes Top-up**: €0.10 per minute
- **Text Tokens Top-up**: €1.00 per 100k tokens

## Step 1: Environment Setup

Add these environment variables to your deployment:

```bash
# Tribute.tg Configuration
TRIBUTE_API=your_tribute_api_key_here
TRIBUTE_WEBHOOK_SECRET=your_webhook_secret_here

# Keep existing variables
BOT_TOKEN=your_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Step 2: Get Tribute API Key

1. Go to https://tribute.tg and create/login to your account
2. Open Author Panel
3. Click three dots (⋯) → Settings
4. Go to "API Keys" section
5. Click "Generate API Key"
6. Copy the key and set it as `TRIBUTE_API` environment variable

## Step 3: Database Migration

Run the database migration to create payment tables:

```bash
# For Supabase
psql -h your-supabase-host -d postgres -U postgres < supabase_migrations/2025-01-08_tribute_billing_migration.sql

# Or apply via Supabase Dashboard → SQL Editor
```

## Step 4: Create Products in Tribute

Run the product setup script:

```bash
# Set your API key
export TRIBUTE_API=your_api_key_here

# Run the setup script
python scripts/setup_tribute_products.py
```

This will create 4 products and output their IDs. **Important**: Copy the product IDs and update them in `app/handlers/tribute.py`:

```python
TRIBUTE_PRODUCT_IDS = {
    "sub_monthly": YOUR_MONTHLY_PRODUCT_ID,
    "sub_yearly": YOUR_YEARLY_PRODUCT_ID,  
    "audio_topup": YOUR_AUDIO_PRODUCT_ID,
    "tokens_topup": YOUR_TOKENS_PRODUCT_ID
}
```

## Step 5: Configure Webhook

1. In Tribute.tg Dashboard → Settings → Webhooks
2. Add webhook URL: `https://n0te-48aa36e910aa.herokuapp.com/billing/tribute/webhook`
3. Select events: "Digital Product Purchase"
4. Generate webhook secret and set it as `TRIBUTE_WEBHOOK_SECRET`

## Step 6: Test Integration

### Test Product Creation
```bash
curl -X GET "https://tribute.tg/api/v1/products" \
  -H "Api-Key: your_api_key_here"
```

### Test Pricing Endpoint
```bash
curl -X GET "https://your-backend-domain.com/billing/pricing"
```

### Test Webhook (Optional)
```bash
curl -X POST "https://your-backend-domain.com/billing/tribute/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Tribute-Signature: test_signature" \
  -d '{"name":"new_digital_product","payload":{"product_id":123,"amount":299}}'
```

## Frontend Integration

Your frontend should call these endpoints:

### Get Pricing
```javascript
const pricing = await fetch('/billing/pricing').then(r => r.json());
```

### Create Purchase
```javascript
const purchase = await fetch('/billing/create-purchase', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    init_data: window.Telegram.WebApp.initData,
    tg_user_id: window.Telegram.WebApp.initDataUnsafe.user.id,
    product_code: 'sub_monthly', // or 'sub_yearly', 'audio_topup', 'tokens_topup'
    quantity: 1
  })
});

// Redirect user to purchase.data.payment_url
window.open(purchase.data.payment_url, '_blank');
```

## Product Configuration

### Monthly Subscription (€2.99)
- Grants unlimited access for 1 month
- Extends existing subscription if active

### Yearly Subscription (€29)
- Grants unlimited access for 1 year  
- 19% discount compared to monthly
- Extends existing subscription if active

### Audio Minutes (€0.10 per minute)
- Top-up additional audio processing time
- Quantity = number of minutes to add

### Text Tokens (€1.00 per 100k tokens)
- Top-up additional text processing tokens
- Quantity = number of 100k token units to add

## Database Schema

The migration creates:

- `payments` table: Tracks all Tribute transactions
- `apply_tribute_payment_effect()` function: Applies payment benefits to users
- Additional columns in `app_users`: `tribute_spent_total`, `preferred_payment_method`

## Troubleshooting

### Common Issues

1. **"TRIBUTE_API not configured"**
   - Ensure environment variable is set correctly
   - Check API key is valid in Tribute dashboard

2. **"Product not configured in Tribute"**
   - Run the setup script to create products
   - Update TRIBUTE_PRODUCT_IDS with actual IDs

3. **"Invalid signature" on webhook**
   - Verify TRIBUTE_WEBHOOK_SECRET matches dashboard
   - Check webhook URL is correct

4. **Database errors**
   - Ensure migration was applied successfully
   - Check Supabase connection and permissions

### Logs to Monitor

- Payment creation: `Successfully processed payment {id} for user {user_id}`
- Webhook errors: `Webhook error: {error}`
- Product setup: Check `tribute_products.json` file

## Security Notes

- Always verify `init_data` from Telegram WebApp
- Validate webhook signatures from Tribute
- Use HTTPS for all webhook endpoints
- Implement rate limiting on payment endpoints
- Log all payment events for compliance

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migration applied  
- [ ] Products created in Tribute.tg
- [ ] Product IDs updated in code
- [ ] Webhook URL configured and tested
- [ ] SSL certificate valid
- [ ] Error handling implemented
- [ ] Payment flow tested end-to-end
- [ ] Monitoring configured
