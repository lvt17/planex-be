-- =====================================================
-- Planex Database Schema for Supabase
-- Generated from Flask-SQLAlchemy models
-- =====================================================

-- Enable UUID extension (optional, for future use)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. STORAGE TABLE (must be created first - no dependencies)
-- =====================================================
CREATE TABLE storage (
    id SERIAL PRIMARY KEY,
    avt_url VARCHAR(500),
    storage_key BYTEA,
    type VARCHAR(50),  -- avatar, image, file
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 2. USERS TABLE
-- =====================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(120),
    storage_id INTEGER REFERENCES storage(id),
    storage_key BYTEA,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- =====================================================
-- 3. TASK TABLE
-- =====================================================
CREATE TABLE task (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    content TEXT,
    deadline TIMESTAMP,
    price FLOAT DEFAULT 0,
    state FLOAT DEFAULT 0,  -- Progress 0-100
    is_done BOOLEAN DEFAULT FALSE,
    client_num VARCHAR(20),
    client_mail VARCHAR(120),
    noted TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_task_user_id ON task(user_id);
CREATE INDEX idx_task_deadline ON task(deadline);
CREATE INDEX idx_task_is_done ON task(is_done);

-- =====================================================
-- 4. WORKSPACE TABLE (subtasks)
-- =====================================================
CREATE TABLE workspace (
    id SERIAL PRIMARY KEY,
    mini_task VARCHAR(200),
    content TEXT,
    loading FLOAT DEFAULT 0,  -- Progress 0-100
    is_done BOOLEAN DEFAULT FALSE
);

-- =====================================================
-- 5. WORKSPACE_MANAGE TABLE (Task-Workspace relationship)
-- =====================================================
CREATE TABLE workspace_manage (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    workspace_id INTEGER NOT NULL REFERENCES workspace(id) ON DELETE CASCADE
);

CREATE INDEX idx_workspace_manage_task ON workspace_manage(task_id);

-- =====================================================
-- 6. WHITEBOARDS TABLE
-- =====================================================
CREATE TABLE whiteboards (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    data JSONB,  -- Store whiteboard elements as JSON
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX idx_whiteboards_user ON whiteboards(user_id);

-- =====================================================
-- 7. WHITEBOARD_ELEMENTS TABLE
-- =====================================================
CREATE TABLE whiteboard_elements (
    id SERIAL PRIMARY KEY,
    whiteboard_id INTEGER NOT NULL REFERENCES whiteboards(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,  -- text, shape, image, etc.
    content JSONB,  -- Element-specific data
    position_x FLOAT DEFAULT 0,
    position_y FLOAT DEFAULT 0,
    width FLOAT DEFAULT 100,
    height FLOAT DEFAULT 50,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_whiteboard_elements_board ON whiteboard_elements(whiteboard_id);

-- =====================================================
-- 8. IMAGES_STORE TABLE
-- =====================================================
CREATE TABLE images_store (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    storage_id INTEGER REFERENCES storage(id),
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_images_store_task ON images_store(task_id);

-- =====================================================
-- 9. ACCOUNT TABLE (for storing external accounts)
-- =====================================================
CREATE TABLE account (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    noted TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 10. ACCOUNTS_STORE TABLE
-- =====================================================
CREATE TABLE accounts_store (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id) ON DELETE CASCADE,
    storage_id INTEGER NOT NULL REFERENCES storage(id) ON DELETE CASCADE
);

-- =====================================================
-- 11. PAYMENT TABLE
-- =====================================================
CREATE TABLE payment (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    card_code VARCHAR(50) NOT NULL,
    content TEXT
);

-- =====================================================
-- 12. PAYMENT_STORE TABLE
-- =====================================================
CREATE TABLE payment_store (
    id SERIAL PRIMARY KEY,
    storage_id INTEGER NOT NULL REFERENCES storage(id) ON DELETE CASCADE,
    payment_id INTEGER NOT NULL REFERENCES payment(id) ON DELETE CASCADE
);

-- =====================================================
-- 13. TOTAL_INCOME TABLE
-- =====================================================
CREATE TABLE total_income (
    id SERIAL PRIMARY KEY,
    total FLOAT DEFAULT 0,
    from_source VARCHAR(200),  -- task_name
    noted TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 14. ONE_INCOME TABLE
-- =====================================================
CREATE TABLE one_income (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    total_income_id INTEGER REFERENCES total_income(id) ON DELETE SET NULL
);

CREATE INDEX idx_one_income_task ON one_income(task_id);

-- =====================================================
-- Enable Row Level Security (RLS) for Supabase
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE task ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_manage ENABLE ROW LEVEL SECURITY;
ALTER TABLE whiteboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE whiteboard_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE images_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE one_income ENABLE ROW LEVEL SECURITY;
ALTER TABLE total_income ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- Done! Your database is ready.
-- =====================================================
