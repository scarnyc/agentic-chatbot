# Database Setup

This directory contains database setup and migration files for the agentic workflow system.

## PostgreSQL Vector Database Setup

### Prerequisites
- PostgreSQL 12+ installed
- `pgvector` extension available

### Setup Instructions

1. **Run the setup script:**
   ```bash
   psql -U postgres -f database/setup_postgres.sql
   ```

2. **Set environment variable:**
   ```bash
   export DATABASE_URL="postgresql://agentic_user:your_secure_password@localhost:5432/agentic_vectors"
   ```
   Or add to your `.env` file:
   ```
   DATABASE_URL=postgresql://agentic_user:your_secure_password@localhost:5432/agentic_vectors
   ```

3. **Verify setup:**
   ```bash
   python -c "from core.vector_db_factory import VectorDBFactory; db = VectorDBFactory.create_vector_db(); print('PostgreSQL setup successful!')"
   ```

## Alternative: Pinecone (Cloud)

If you prefer a cloud vector database, you can use Pinecone instead:

1. **Get Pinecone API key** from [pinecone.io](https://pinecone.io)

2. **Set environment variable:**
   ```bash
   export PINECONE_API_KEY="your-pinecone-api-key"
   ```

## Fallback: Mock Database

If neither PostgreSQL nor Pinecone is configured, the system will automatically use a mock database for development. This provides basic functionality but doesn't persist data between restarts.

## Files in this directory

- `setup_postgres.sql` - PostgreSQL database and user creation script
- `README.md` - This documentation file

## Related Core Files

The database implementations are located in the `core/` directory:
- `core/postgres_vector_db.py` - PostgreSQL vector database implementation
- `core/vector_db_factory.py` - Factory for creating database instances
- `core/mock_vector_db.py` - Mock database for testing/fallback