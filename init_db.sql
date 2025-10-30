-- PostgreSQL initialization script for facial processing cache
-- This script sets up the database with proper permissions and initial configuration

-- Create extension for UUID generation (if not exists)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for performance monitoring (optional)
-- Note: This extension might not be available in all PostgreSQL installations
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE facial_processing TO postgres;

-- Note: Tables, views, and functions will be created by the application
-- during startup after SQLAlchemy creates the schema
-- Performance parameters can be set via environment variables or postgresql.conf

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL facial processing cache database initialized successfully';
    RAISE NOTICE 'Tables and views will be created by the application during startup';
END $$;