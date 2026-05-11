-- DisasterGuard Database Setup Script
-- Run this script to create the required tables

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    phone VARCHAR(50),
    location VARCHAR(255),
    ip_address VARCHAR(50),
    provider VARCHAR(50) DEFAULT 'local',
    provider_id VARCHAR(255),
    profile_picture VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create alerts table (for future use)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(100),
    message TEXT,
    severity VARCHAR(50),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
);

-- Create predictions table (for future use)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    location VARCHAR(255),
    risk_level VARCHAR(50),
    probability INTEGER,
    prediction_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample admin user (password: admin123)
INSERT INTO users (name, email, password, role, status) 
VALUES ('Admin', 'admin@disasterguard.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin', 'active')
ON CONFLICT (email) DO NOTHING;

-- Insert sample regular user
INSERT INTO users (name, email, password, role, status) 
VALUES ('Test User', 'user@test.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'user', 'active')
ON CONFLICT (email) DO NOTHING;
