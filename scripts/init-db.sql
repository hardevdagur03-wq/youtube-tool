-- Database initialization script
-- Run automatically on first PostgreSQL container start

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
ALTER DATABASE "${DB_NAME:-yt_blog}" SET search_path TO app, public, audit;

-- Create application user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER:-ytblog}') THEN
        CREATE ROLE ${DB_USER:-ytblog} WITH LOGIN PASSWORD '${DB_PASSWORD:-changeme}';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME:-yt_blog}" TO ${DB_USER:-ytblog};
GRANT ALL PRIVILEGES ON SCHEMA app TO ${DB_USER:-ytblog};
GRANT ALL PRIVILEGES ON SCHEMA audit TO ${DB_USER:-ytblog};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO ${DB_USER:-ytblog};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO ${DB_USER:-ytblog};
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO ${DB_USER:-ytblog};
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO ${DB_USER:-ytblog};
