"""
Tribute.tg payment integration handler
Handles payment creation, webhooks, and user billing
"""

import os
import json
import hmac
import hashlib
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request
from pydantic import BaseModel

from ..config import settings
from ..supabase_client import get_supabase


class CreatePurchaseRequest(BaseModel):
    init_data: str
    tg_user_id: int
    product_code: str
    quantity: int = 1


# Product mapping to Tribute.tg product IDs
# Update these with actual IDs after running the setup script
TRIBUTE_PRODUCT_IDS = {
    "sub_monthly": YOUR_MONTHLY_PRODUCT_ID,
    "sub_yearly": YOUR_YEARLY_PRODUCT_ID,  
    "audio_topup": YOUR_AUDIO_PRODUCT_ID,
    "tokens_topup": YOUR_TOKENS_PRODUCT_ID
}

# Pricing configuration in EUR cents
PRODUCT_PRICING = {
    "sub_monthly": {
        "amount": 299,  # €2.99
        "currency": "eur",
        "name": "Monthly Subscription"
    },
    "sub_yearly": {
        "amount": 2900,  # €29 (19% discount)
        "currency": "eur", 
        "name": "Yearly Subscription",
        "discount": 19
    },
    "audio_topup": {
        "amount": 10,  # €0.10 per minute
        "currency": "eur",
        "name": "Audio Minutes",
        "unit": "minute"
    },
    "tokens_topup": {
        "amount": 100,  # €1.00 per 100k tokens
        "currency": "eur",
        "name": "Text Tokens", 
        "unit": "100k tokens"
    }
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


def verify_tribute_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Tribute.tg webhook signature"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


async def get_or_create_user(tg_user_id: int) -> Dict[str, Any]:
    """Get or create user in database"""
    supabase = get_supabase()
    
    # Try to find existing user
    result = supabase.table("app_users").select("*").eq("tg_user_id", tg_user_id).execute()
    
    if result.data:
        return result.data[0]
    
    # Create new user
    user_data = {
        "tg_user_id": tg_user_id,
        "subscription_status": "none",
        "privacy_accepted": True,  # Assume accepted if making payment
    }
    
    result = supabase.table("app_users").insert(user_data).execute()
    return result.data[0]


async def create_tribute_payment_link(product_id: int, quantity: int = 1) -> str:
    """Create payment link via Tribute.tg API"""
    api_key = os.getenv("TRIBUTE_API")
    if not api_key:
        raise ValueError("TRIBUTE_API not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            # Get product information
            response = await client.get(
                f"https://tribute.tg/api/v1/products/{product_id}",
                headers={"Api-Key": api_key}
            )
            response.raise_for_status()
            product_data = response.json()
            
            # Return the payment link
            return product_data.get("webLink", f"https://tribute.tg/product/{product_id}")
            
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to get product link: {e}")


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
    supabase = get_supabase()
    
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
    
    result = supabase.table("payments").insert(payment_data).execute()
    return str(result.data[0]["id"])


async def get_pricing():
    """Get current product pricing"""
    return PRODUCT_PRICING


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
        user_data = json.loads(init_data_parsed.get("user", "{}"))
        if str(tg_user_id) != str(user_data.get("id")):
            raise ValueError("User ID mismatch")
        
        # Get or create user
        user = await get_or_create_user(tg_user_id)
        
        # Get product configuration
        if request.product_code not in TRIBUTE_PRODUCT_IDS:
            raise ValueError(f"Unknown product code: {request.product_code}")
        
        tribute_product_id = TRIBUTE_PRODUCT_IDS[request.product_code]
        if not tribute_product_id:
            raise ValueError(f"Product {request.product_code} not configured in Tribute")
        
        # Calculate pricing
        pricing = await get_pricing()
        product_pricing = pricing[request.product_code]
        total_amount = product_pricing["amount"] * request.quantity
        
        # Create payment record
        payment_id = await create_payment_record(
            user_id=user["id"],
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
            "currency": product_pricing["currency"],
            "payment_id": payment_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def handle_tribute_webhook(request: Request):
    """Handle Tribute.tg webhook notifications"""
    try:
        payload = await request.body()
        signature = request.headers.get("X-Tribute-Signature", "")
        
        # Verify webhook signature
        webhook_secret = os.getenv("TRIBUTE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        if not verify_tribute_webhook(payload, signature, webhook_secret):
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
    supabase = get_supabase()
    payload = webhook_data.get("payload", {})
    
    product_id = payload.get("product_id")
    amount = payload.get("amount")  # Amount in cents
    currency = payload.get("currency", "eur")
    telegram_user_id = payload.get("telegram_user_id")
    charge_id = payload.get("charge_id")
    
    # Find corresponding payment record
    result = supabase.table("payments").select("*").eq("tribute_product_id", product_id).eq("status", "pending").eq("tg_user_id", telegram_user_id).order("created_at", desc=True).limit(1).execute()
    
    if not result.data:
        print(f"Payment record not found for product {product_id}, user {telegram_user_id}")
        return
    
    payment = result.data[0]
    
    # Update payment status
    supabase.table("payments").update({
        "status": "paid",
        "paid_at": datetime.utcnow().isoformat(),
        "tribute_webhook_data": webhook_data,
        "tribute_charge_id": charge_id,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payment["id"]).execute()
    
    # Apply payment effects using RPC call to database function
    supabase.rpc("apply_tribute_payment_effect", {
        "p_user_id": payment["user_id"],
        "p_product_code": payment["product_code"],
        "p_quantity": payment["quantity"],
        "p_total_amount": payment["total_amount"],
        "p_currency": payment["original_currency"]
    }).execute()
    
    # Update user's total Tribute spending
    supabase.table("app_users").update({
        "tribute_spent_total": supabase.table("app_users").select("tribute_spent_total").eq("id", payment["user_id"]).execute().data[0]["tribute_spent_total"] + payment["total_amount"],
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payment["user_id"]).execute()
    
    print(f"Successfully processed payment {payment['id']} for user {telegram_user_id}")
