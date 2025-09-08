-- Migration for Tribute.tg billing integration
-- Creates tables and functions for handling Tribute payments

-- Create payments table for tracking Tribute transactions
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    tg_user_id BIGINT NOT NULL,
    
    -- Product information
    product_code TEXT NOT NULL, -- 'sub_monthly', 'sub_yearly', 'audio_topup', 'tokens_topup'
    quantity INTEGER NOT NULL DEFAULT 1,
    tribute_product_id INTEGER NOT NULL,
    
    -- Pricing information
    total_amount INTEGER NOT NULL, -- Amount in cents
    currency TEXT NOT NULL DEFAULT 'eur',
    original_currency TEXT NOT NULL DEFAULT 'eur',
    
    -- Payment status
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'paid', 'failed', 'refunded'
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Tribute.tg webhook data
    tribute_webhook_data JSONB,
    tribute_charge_id TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_tg_user_id ON payments(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_tribute_product_id ON payments(tribute_product_id);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_payments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payments_updated_at_trigger
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_payments_updated_at();

-- Function to apply payment effects to user account
CREATE OR REPLACE FUNCTION apply_tribute_payment_effect(
    p_user_id UUID,
    p_product_code TEXT,
    p_quantity INTEGER,
    p_total_amount INTEGER,
    p_currency TEXT
) RETURNS VOID AS $$
DECLARE
    current_subscription_status TEXT;
    current_renew_at TIMESTAMP WITH TIME ZONE;
    new_renew_at TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Get current user subscription info
    SELECT subscription_status, subscription_renew_at 
    INTO current_subscription_status, current_renew_at
    FROM app_users 
    WHERE id = p_user_id;
    
    -- Apply effects based on product type
    CASE p_product_code
        WHEN 'sub_monthly' THEN
            -- Monthly subscription
            IF current_subscription_status = 'active' AND current_renew_at > NOW() THEN
                -- Extend existing subscription
                new_renew_at := current_renew_at + INTERVAL '1 month';
            ELSE
                -- New subscription
                new_renew_at := NOW() + INTERVAL '1 month';
            END IF;
            
            UPDATE app_users 
            SET 
                subscription_status = 'active',
                subscription_renew_at = new_renew_at,
                updated_at = NOW()
            WHERE id = p_user_id;
            
        WHEN 'sub_yearly' THEN
            -- Yearly subscription
            IF current_subscription_status = 'active' AND current_renew_at > NOW() THEN
                -- Extend existing subscription
                new_renew_at := current_renew_at + INTERVAL '1 year';
            ELSE
                -- New subscription
                new_renew_at := NOW() + INTERVAL '1 year';
            END IF;
            
            UPDATE app_users 
            SET 
                subscription_status = 'active',
                subscription_renew_at = new_renew_at,
                updated_at = NOW()
            WHERE id = p_user_id;
            
        WHEN 'audio_topup' THEN
            -- Add audio minutes (quantity is in minutes)
            UPDATE app_users 
            SET 
                audio_minutes_total = audio_minutes_total + (p_quantity * 60), -- Convert to seconds
                updated_at = NOW()
            WHERE id = p_user_id;
            
        WHEN 'tokens_topup' THEN
            -- Add text tokens (quantity is in 100k token units)
            UPDATE app_users 
            SET 
                text_tokens_used_total = text_tokens_used_total + (p_quantity * 100000),
                updated_at = NOW()
            WHERE id = p_user_id;
            
        ELSE
            RAISE EXCEPTION 'Unknown product code: %', p_product_code;
    END CASE;
    
    -- Log the payment application
    RAISE NOTICE 'Applied payment effect for user % - product: %, quantity: %', 
        p_user_id, p_product_code, p_quantity;
END;
$$ LANGUAGE plpgsql;

-- Add Tribute-related columns to app_users if they don't exist
DO $$
BEGIN
    -- Add column to track total Tribute spending
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'app_users' AND column_name = 'tribute_spent_total') THEN
        ALTER TABLE app_users ADD COLUMN tribute_spent_total INTEGER NOT NULL DEFAULT 0;
    END IF;
    
    -- Add column to track payment method preference
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'app_users' AND column_name = 'preferred_payment_method') THEN
        ALTER TABLE app_users ADD COLUMN preferred_payment_method TEXT DEFAULT 'tribute';
    END IF;
END $$;

-- Create view for payment analytics
CREATE OR REPLACE VIEW payment_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as payment_date,
    product_code,
    COUNT(*) as payment_count,
    SUM(total_amount) as total_revenue_cents,
    SUM(total_amount) / 100.0 as total_revenue_euros,
    AVG(total_amount) / 100.0 as avg_payment_euros,
    COUNT(DISTINCT user_id) as unique_users
FROM payments 
WHERE status = 'paid'
GROUP BY DATE_TRUNC('day', created_at), product_code
ORDER BY payment_date DESC, product_code;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON payments TO authenticated;
GRANT SELECT ON payment_analytics TO authenticated;
GRANT USAGE ON SEQUENCE payments_id_seq TO authenticated;

COMMENT ON TABLE payments IS 'Tracks all Tribute.tg payment transactions';
COMMENT ON FUNCTION apply_tribute_payment_effect IS 'Applies payment effects to user account after successful Tribute payment';
COMMENT ON VIEW payment_analytics IS 'Analytics view for payment data grouped by date and product';
