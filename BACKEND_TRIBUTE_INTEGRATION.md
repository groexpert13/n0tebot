# Backend Integration Guide: Tribute.tg Payment System

## Overview

This guide provides complete backend implementation recommendations for integrating Tribute.tg payment system into n0tes, replacing the current Telegram Stars billing.

## Prerequisites

1. **Tribute.tg Account Setup**
   - Create account at https://tribute.tg
   - Generate API key from Author Panel → Settings → API Keys
   - Set up webhook URL in Tribute.tg dashboard

2. **Environment Variables**
   ```bash
   TRIBUTE_API=your_tribute_api_key_here
   TRIBUTE_WEBHOOK_SECRET=your_webhook_secret_here
   NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
   ```

## Database Migration

Run the provided SQL migration:
```bash
psql -d your_database < sql/2025-01-08_tribute_billing_migration.sql
```

## API Endpoints Implementation

### 1. GET /billing/pricing

Returns current product pricing information.

```python
@app.get("/billing/pricing")
async def get_pricing():
    """Get current product pricing from Tribute.tg or return cached values"""
    return {
        "sub_monthly": {
            "amount": 299,  # €2.99 in cents
            "currency": "eur"
        },
        "sub_yearly": {
            "amount": 2900,  # €29 in cents
            "currency": "eur",
            "discount": 19  # 19% discount vs monthly
        },
        "audio_topup": {
            "amount": 10,  # €0.10 per minute
            "currency": "eur",
            "unit": "minute"
        },
        "tokens_topup": {
            "amount": 100,  # €1.00 per 100k tokens
            "currency": "eur",
            "unit": "100k tokens"
        }
    }
```

### 2. POST /billing/create-purchase

Creates a purchase via Tribute.tg and returns payment URL.

```python
import httpx
import hashlib
import hmac
from urllib.parse import parse_qsl

# Product mapping to Tribute.tg product IDs (set these after creating products)
TRIBUTE_PRODUCT_IDS = {
    "sub_monthly": 1234,    # Replace with actual product ID
    "sub_yearly": 1235,     # Replace with actual product ID  
    "audio_topup": 1236,    # Replace with actual product ID
    "tokens_topup": 1237    # Replace with actual product ID
}

def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """Verify Telegram WebApp init_data signature"""
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_value = parsed_data.pop('hash', '')
        
        # Create data check string
        data_check_arr = []
        for key, value in sorted(parsed_data.items()):
            data_check_arr.append(f"{key}={value}")
        data_check_string = '\n'.join(data_check_arr)
        
        # Create secret key
        secret_key = hmac.new(
            b"WebAppData", 
            bot_token.encode(), 
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != hash_value:
            raise ValueError("Invalid hash")
            
        return parsed_data
    except Exception as e:
        raise ValueError(f"Invalid init_data: {e}")

async def create_tribute_payment_link(product_id: int, quantity: int = 1) -> str:
    """Create payment link via Tribute.tg API"""
    async with httpx.AsyncClient() as client:
        # For variable quantity products, we need to create custom pricing
        # This is a simplified example - you may need to create products dynamically
        # or use Tribute.tg's custom pricing features
        
        response = await client.get(
            f"https://tribute.tg/api/v1/products/{product_id}",
            headers={"Api-Key": os.getenv("TRIBUTE_API")}
        )
        response.raise_for_status()
        product_data = response.json()
        
        # Return the payment link
        return product_data["webLink"]

@app.post("/billing/create-purchase")
async def create_purchase(request: CreatePurchaseRequest):
    """Create a purchase via Tribute.tg"""
    try:
        # Verify Telegram WebApp init_data
        init_data_parsed = verify_telegram_init_data(
            request.init_data, 
            os.getenv("BOT_TOKEN")
        )
        
        # Validate user
        tg_user_id = request.tg_user_id
        if str(tg_user_id) != init_data_parsed.get("user", {}).get("id"):
            raise ValueError("User ID mismatch")
        
        # Get or create user
        user = await get_or_create_user(tg_user_id)
        
        # Get product configuration
        if request.product_code not in TRIBUTE_PRODUCT_IDS:
            raise ValueError(f"Unknown product code: {request.product_code}")
        
        tribute_product_id = TRIBUTE_PRODUCT_IDS[request.product_code]
        
        # Calculate pricing
        pricing = await get_pricing()
        product_pricing = pricing[request.product_code]
        total_amount = product_pricing["amount"] * request.quantity
        
        # Create payment record
        payment_id = await create_payment_record(
            user_id=user.id,
            tg_user_id=tg_user_id,
            product_code=request.product_code,
            quantity=request.quantity,
            tribute_product_id=tribute_product_id,
            total_amount=total_amount,
            currency=product_pricing["currency"]
        )
        
        # Get payment link from Tribute.tg
        payment_url = await create_tribute_payment_link(
            tribute_product_id, 
            request.quantity
        )
        
        return {
            "payment_url": payment_url,
            "product_id": tribute_product_id,
            "total_amount": total_amount,
            "currency": product_pricing["currency"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def create_payment_record(
    user_id: str,
    tg_user_id: int,
    product_code: str,
    quantity: int,
    tribute_product_id: int,
    total_amount: int,
    currency: str
) -> str:
    """Create payment record in database"""
    payment_data = {
        "user_id": user_id,
        "tg_user_id": tg_user_id,
        "product_code": product_code,
        "quantity": quantity,
        "tribute_product_id": tribute_product_id,
        "total_amount": total_amount,
        "currency": currency,
        "original_currency": currency,
        "status": "pending"
    }
    
    # Insert into database (adjust for your ORM/database client)
    result = await db.payments.insert(payment_data)
    return result.id
```

### 3. POST /tribute/webhook

Handles Tribute.tg webhooks for payment confirmation.

```python
import json
from datetime import datetime

def verify_tribute_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Tribute.tg webhook signature"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.post("/tribute/webhook")
async def tribute_webhook(request: Request):
    """Handle Tribute.tg webhook notifications"""
    try:
        payload = await request.body()
        signature = request.headers.get("X-Tribute-Signature", "")
        
        # Verify webhook signature
        if not verify_tribute_webhook(
            payload, 
            signature, 
            os.getenv("TRIBUTE_WEBHOOK_SECRET")
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        webhook_data = json.loads(payload)
        
        # Handle different webhook events
        event_name = webhook_data.get("name")
        
        if event_name == "new_digital_product":
            await handle_digital_product_purchase(webhook_data)
        else:
            print(f"Unhandled webhook event: {event_name}")
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def handle_digital_product_purchase(webhook_data: dict):
    """Handle successful digital product purchase"""
    payload = webhook_data.get("payload", {})
    
    product_id = payload.get("product_id")
    amount = payload.get("amount")  # Amount in cents
    currency = payload.get("currency", "eur")
    telegram_user_id = payload.get("telegram_user_id")
    
    # Find corresponding payment record
    payment = await db.payments.find_one({
        "tribute_product_id": product_id,
        "status": "pending",
        "tg_user_id": telegram_user_id
    })
    
    if not payment:
        print(f"Payment record not found for product {product_id}")
        return
    
    # Update payment status
    await db.payments.update(payment.id, {
        "status": "paid",
        "paid_at": datetime.utcnow(),
        "tribute_webhook_data": webhook_data
    })
    
    # Apply payment effects using the database function
    await db.execute(
        "SELECT apply_tribute_payment_effect($1, $2, $3, $4, $5)",
        payment.user_id,
        payment.product_code,
        payment.quantity,
        payment.total_amount,
        payment.original_currency
    )
    
    print(f"Successfully processed payment {payment.id}")
```

## Product Setup Script

Use the provided script to create products in Tribute.tg:

```bash
# Set your API key
export TRIBUTE_API=your_api_key_here

# Run the setup script
node scripts/setup-tribute-products.js
```

After running the script, update `TRIBUTE_PRODUCT_IDS` in your backend with the returned product IDs.

## Webhook Configuration

1. **In Tribute.tg Dashboard:**
   - Go to Settings → Webhooks
   - Add webhook URL: `https://your-backend-domain.com/tribute/webhook`
   - Select events: "Digital Product Purchase"
   - Set webhook secret and save it to `TRIBUTE_WEBHOOK_SECRET`

2. **Test Webhook:**
   ```bash
   curl -X POST https://your-backend-domain.com/tribute/webhook \
     -H "Content-Type: application/json" \
     -H "X-Tribute-Signature: test" \
     -d '{"name":"new_digital_product","payload":{"product_id":123,"amount":299}}'
   ```

## Security Considerations

1. **Always verify init_data** from Telegram WebApp
2. **Validate webhook signatures** from Tribute.tg
3. **Use HTTPS** for all webhook endpoints
4. **Implement rate limiting** on payment endpoints
5. **Log all payment events** for debugging and compliance
6. **Use environment variables** for sensitive configuration

## Error Handling

```python
class PaymentError(Exception):
    pass

class WebhookError(Exception):
    pass

# Add proper error handling to all endpoints
@app.exception_handler(PaymentError)
async def payment_error_handler(request: Request, exc: PaymentError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "code": "PAYMENT_ERROR"}
    )
```

## Testing

1. **Unit Tests:**
   - Test init_data verification
   - Test webhook signature verification
   - Test payment record creation

2. **Integration Tests:**
   - Test complete payment flow
   - Test webhook processing
   - Test user balance updates

3. **Manual Testing:**
   - Create test products in Tribute.tg
   - Test payment flow from frontend
   - Verify webhook delivery and processing

## Monitoring

1. **Log all payment events**
2. **Monitor webhook delivery success rates**
3. **Track payment conversion rates**
4. **Set up alerts for failed payments**
5. **Monitor database performance for payment queries**

## Migration from Telegram Stars

1. **Keep existing Stars billing** during transition period
2. **Add feature flag** to switch between payment systems
3. **Migrate existing subscriptions** gradually
4. **Provide clear communication** to users about the change
5. **Monitor payment success rates** during migration

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migration applied
- [ ] Products created in Tribute.tg
- [ ] Webhook URL configured and tested
- [ ] SSL certificate valid for webhook endpoint
- [ ] Error handling and logging implemented
- [ ] Payment flow tested end-to-end
- [ ] Monitoring and alerts configured
- [ ] Backup and recovery procedures documented
