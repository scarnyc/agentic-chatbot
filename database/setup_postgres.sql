-- setup_postgres.sql
-- PostgreSQL setup script for agentic vector database

-- Connect to PostgreSQL as superuser and run these commands:

-- 1. Create database for vector storage
CREATE DATABASE agentic_vectors;

-- 2. Connect to the new database
\c agentic_vectors;

-- 3. Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 4. Create user for the application (optional, for security)
-- Replace 'your_username' and 'your_password' with actual values
CREATE USER agentic_user WITH PASSWORD 'your_secure_password';

-- 5. Grant necessary permissions
GRANT CONNECT ON DATABASE agentic_vectors TO agentic_user;
GRANT USAGE ON SCHEMA public TO agentic_user;
GRANT CREATE ON SCHEMA public TO agentic_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agentic_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agentic_user;

-- 6. Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO agentic_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO agentic_user;

-- 7. Verify pgvector installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Expected output should show the vector extension is installed

-- 8. Test vector operations
SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector AS cosine_distance;

-- Expected output should show a cosine distance value (e.g., 0.028)

\echo 'PostgreSQL vector database setup complete!'
\echo 'Connection string: postgresql://agentic_user:your_secure_password@localhost:5432/agentic_vectors'