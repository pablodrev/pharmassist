-- Initialize database for PharmAssist
-- This script runs automatically when PostgreSQL container starts

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS pharmadb;

-- Note: PostgreSQL doesn't allow CREATE DATABASE in a transaction
-- The database creation is handled by POSTGRES_DB env variable
-- This script just ensures everything is set up correctly
