#!/usr/bin/env python3
"""
Script to create digital products in Tribute.tg via API
Run this script to set up all required products for n0te bot
"""

import os
import httpx
import asyncio
import json
from typing import Dict, Any

# Product configurations
PRODUCTS = [
    {
        "name": "n0te Monthly Subscription",
        "description": "Monthly subscription for unlimited access to n0te AI assistant",
        "price": 299,  # €2.99 in cents
        "currency": "EUR",
        "type": "digital",
        "code": "sub_monthly"
    },
    {
        "name": "n0te Yearly Subscription", 
        "description": "Yearly subscription for unlimited access to n0te AI assistant (19% discount)",
        "price": 2900,  # €29 in cents (19% discount from 12*2.99=35.88)
        "currency": "EUR", 
        "type": "digital",
        "code": "sub_yearly"
    },
    {
        "name": "Audio Minutes Top-up",
        "description": "Additional audio processing minutes for n0te",
        "price": 10,  # €0.10 per minute
        "currency": "EUR",
        "type": "digital", 
        "code": "audio_topup"
    },
    {
        "name": "Text Tokens Top-up",
        "description": "Additional text processing tokens for n0te", 
        "price": 100,  # €1.00 per 100k tokens
        "currency": "EUR",
        "type": "digital",
        "code": "tokens_topup"
    }
]

async def create_tribute_product(api_key: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a product in Tribute.tg via API"""
    async with httpx.AsyncClient() as client:
        try:
            # Note: This is a placeholder implementation
            # The actual Tribute.tg API endpoint for creating products may differ
            # You'll need to check the official API documentation for the correct endpoint
            
            response = await client.post(
                "https://tribute.tg/api/v1/products",
                headers={
                    "Api-Key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "name": product_data["name"],
                    "description": product_data["description"], 
                    "price": product_data["price"],
                    "currency": product_data["currency"],
                    "type": product_data["type"],
                    "digital": True,
                    "metadata": {
                        "product_code": product_data["code"],
                        "bot": "n0te"
                    }
                }
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Created product: {product_data['name']} (ID: {result.get('id')})")
                return result
            else:
                print(f"❌ Failed to create product {product_data['name']}: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating product {product_data['name']}: {e}")
            return None

async def main():
    """Main function to create all products"""
    api_key = os.getenv("TRIBUTE_API")
    
    if not api_key:
        print("❌ TRIBUTE_API environment variable not set")
        print("Please set your Tribute.tg API key:")
        print("export TRIBUTE_API=your_api_key_here")
        return
    
    print("🚀 Creating products in Tribute.tg...")
    print(f"Using API key: {api_key[:10]}...")
    
    created_products = {}
    
    for product in PRODUCTS:
        print(f"\n📦 Creating product: {product['name']}")
        result = await create_tribute_product(api_key, product)
        
        if result:
            created_products[product['code']] = {
                'id': result.get('id'),
                'name': product['name'],
                'price': product['price'],
                'currency': product['currency']
            }
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    # Output results
    print("\n" + "="*50)
    print("📋 PRODUCT CREATION SUMMARY")
    print("="*50)
    
    if created_products:
        print("\n✅ Successfully created products:")
        for code, data in created_products.items():
            print(f"  {code}: ID {data['id']} - {data['name']} ({data['price']/100:.2f} {data['currency']})")
        
        print("\n🔧 Add these product IDs to your backend configuration:")
        print("TRIBUTE_PRODUCT_IDS = {")
        for code, data in created_products.items():
            print(f'    "{code}": {data["id"]},')
        print("}")
        
        # Save to file for reference
        with open("tribute_products.json", "w") as f:
            json.dump(created_products, f, indent=2)
        print("\n💾 Product data saved to tribute_products.json")
        
    else:
        print("\n❌ No products were created successfully")
        print("Please check your API key and try again")

if __name__ == "__main__":
    asyncio.run(main())
