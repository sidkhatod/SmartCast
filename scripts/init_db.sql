-- SmartCast Database Initialization Script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for performance (these will be created by SQLAlchemy)
-- This script is mainly for initial data and manual setup

-- Insert default admin user (password: admin123)
-- Note: This will be handled by the application, but kept here for reference
-- INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser, is_streamer)
-- VALUES (
--     'admin',
--     'admin@smartcast.com', 
--     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdXzgKM5JM7TK',
--     'Administrator',
--     true,
--     true,
--     true
-- ) ON CONFLICT (username) DO NOTHING;

-- Sample stream categories
CREATE TABLE IF NOT EXISTS stream_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO stream_categories (name, description) VALUES
('Gaming', 'Video game streams and content'),
('Music', 'Live music performances and DJ sets'),
('Talk Shows', 'Podcasts and discussion shows'), 
('Education', 'Educational content and tutorials'),
('Sports', 'Sports broadcasts and commentary'),
('Art', 'Creative arts and drawing streams'),
('Technology', 'Programming and tech discussions')
ON CONFLICT (name) DO NOTHING;

-- Performance indexes (will be created by SQLAlchemy, but listed here for reference)
-- CREATE INDEX IF NOT EXISTS idx_streams_status ON streams(status);
-- CREATE INDEX IF NOT EXISTS idx_streams_is_live ON streams(is_live);
-- CREATE INDEX IF NOT EXISTS idx_streams_created_at ON streams(created_at);
-- CREATE INDEX IF NOT EXISTS idx_streams_user_id ON streams(user_id);
-- CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
-- CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_room_id ON chat_messages(chat_room_id);
-- CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
