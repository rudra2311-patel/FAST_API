-- Add new columns to notification_logs table for deduplication and read tracking
-- Run this in your PostgreSQL database

-- Add is_read column
ALTER TABLE notification_logs 
ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT false;

-- Add fcm_message_id column (stores FCM message ID for tracking)
ALTER TABLE notification_logs 
ADD COLUMN IF NOT EXISTS fcm_message_id VARCHAR(500);

-- Add notification_hash column (for deduplication - prevents same notification in 24h)
ALTER TABLE notification_logs 
ADD COLUMN IF NOT EXISTS notification_hash VARCHAR(100);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_notification_hash ON notification_logs(notification_hash);
CREATE INDEX IF NOT EXISTS idx_notification_created_at ON notification_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notification_logs(is_read);
CREATE INDEX IF NOT EXISTS idx_notification_user_created ON notification_logs(user_id, created_at DESC);

-- Show current structure
\d notification_logs;

-- Check existing notifications
SELECT 
    COUNT(*) as total_notifications,
    COUNT(*) FILTER (WHERE is_read = true) as read_count,
    COUNT(*) FILTER (WHERE is_read = false) as unread_count
FROM notification_logs;
