# Vector Database Setup Guide for FF_Agent

## Overview
This guide explains how to set up and use the vector database enhancement for your FF_Agent, which provides semantic search and query learning capabilities.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Add to your `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
NEON_CONNECTION_STRING=your_neon_connection_string_here
```

### 3. Initialize Vector Database
Run the setup script to create tables and indexes:
```bash
python setup_vector_db.py
```

This will:
- Enable pgvector extension in your Neon database
- Create tables for query embeddings, schema embeddings, and error patterns
- Index your database schema for semantic search
- Seed example queries for initial context

### 4. Update Your Schema
Edit `setup_vector_db.py` to add your actual database schema:
```python
sample_schema = [
    {"table_name": "your_table", "column_name": "your_column", "description": "What this column contains"},
    # Add all your tables and columns
]
```

### 5. Switch to Enhanced API
Replace your API startup command:
```bash
# Old
python api.py

# New - with vector search
python api_enhanced.py
```

## How It Works

### Query Flow
1. **User asks question** → "Show inactive customers"
2. **Vector search finds similar past queries** → Finds "Find customers with no orders"
3. **LLM gets context** → Past SQL examples + relevant schema
4. **Better SQL generation** → More accurate query
5. **Learning loop** → Successful query stored for future

### Features

#### Semantic Query Understanding
- Finds similar questions even with different wording
- "inactive customers" ≈ "customers who haven't ordered"

#### Dynamic Schema Discovery
- Automatically finds relevant tables based on question
- No more hard-coding table relationships

#### Error Learning
- Tracks failed queries to avoid repeating mistakes
- Improves accuracy over time

#### Performance Metrics
- Tracks execution times
- Success rates for different query patterns

## API Endpoints

### `/query` - Execute Query
```json
POST /query
{
    "question": "Show top selling products",
    "use_vector_search": true  // Optional, default true
}
```

Response includes:
- `vector_context_used`: Whether vector search was used
- `similar_queries_found`: Number of similar past queries found

### `/stats` - Get Statistics
```json
GET /stats

Response:
{
    "query_patterns": {
        "total": 42,
        "avg_success_rate": 0.95
    },
    "schema_items": 35,
    "error_patterns": {
        "total": 5,
        "resolved": 3
    }
}
```

## Testing

### 1. Test Vector Search
```python
from vector_store import VectorStore

vs = VectorStore()
similar = vs.find_similar_queries("Show inactive customers")
print(similar)
```

### 2. Test API
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show customers who ordered this month"}'
```

## Monitoring

The system automatically:
- Stores successful queries for reuse
- Tracks error patterns
- Updates success rates
- Maintains execution time averages

Check statistics endpoint regularly to monitor improvement.

## Troubleshooting

### pgvector not found
```sql
-- Run in Neon SQL editor
CREATE EXTENSION vector;
```

### OpenAI API errors
- Check API key in .env
- Verify quota/billing

### Slow similarity search
- Rebuild indexes after adding many embeddings:
```sql
REINDEX INDEX query_embedding_idx;
```

## Next Steps

1. **Add more schema descriptions** - Better semantic understanding
2. **Train with real queries** - Import your query history
3. **Fine-tune similarity threshold** - Adjust based on your data
4. **Add query categories** - Group similar query types

## Benefits Over Time

- **Week 1**: Basic similarity matching
- **Week 2**: Learns common query patterns
- **Month 1**: Significant accuracy improvement
- **Month 2+**: Near-perfect for common queries

The more you use it, the smarter it gets!