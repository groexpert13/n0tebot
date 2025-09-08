"""
Billing API routes for Tribute.tg integration
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..handlers.tribute import (
    get_pricing,
    create_purchase,
    handle_tribute_webhook,
    CreatePurchaseRequest
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.options("/pricing")
async def pricing_options():
    """Handle CORS preflight for pricing endpoint"""
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    })

@router.get("/pricing")
async def get_pricing_endpoint():
    """Get current product pricing information"""
    try:
        pricing = await get_pricing()
        return {
            "success": True,
            "data": pricing
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/create-purchase")
async def create_purchase_options():
    """Handle CORS preflight for create-purchase endpoint"""
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    })

@router.post("/create-purchase")
async def create_purchase_endpoint(request: CreatePurchaseRequest):
    """Create a purchase via Tribute.tg and return payment URL"""
    try:
        result = await create_purchase(request)
        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tribute/webhook")
async def tribute_webhook_endpoint(request: Request):
    """Handle Tribute.tg webhook notifications"""
    try:
        result = await handle_tribute_webhook(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Alternative webhook endpoint (matches the recommended URL format)
@router.post("/webhook")
async def tribute_webhook_alt_endpoint(request: Request):
    """Alternative webhook endpoint for Tribute.tg"""
    return await tribute_webhook_endpoint(request)
