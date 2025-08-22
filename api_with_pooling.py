#!/usr/bin/env python3
"""
Enhanced API with connection pooling to prevent SSL timeouts
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, Any, List
import json
from vector_store_cached import CachedVectorStore

load_dotenv()

app = FastAPI(title="FF_Agent API - Stable")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Create engine with NullPool to avoid connection issues
engine = create_engine(
    os.getenv("NEON_DATABASE_URL"),
    poolclass=NullPool,  # Disable connection pooling
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30 second timeout
    }
)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    success: bool
    question: str
    sql: str = None
    data: Any = None
    error: str = None
    row_count: int = 0

def get_schema():
    """Get database schema"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """))
            
            schema = {}
            for row in result:
                if row.table_name not in schema:
                    schema[row.table_name] = []
                schema[row.table_name].append({
                    'column': row.column_name,
                    'type': row.data_type
                })
            return schema
    except Exception as e:
        print(f"Schema error: {e}")
        return {}

def generate_sql(question: str) -> str:
    """Generate SQL from natural language"""
    schema = get_schema()
    
    # Format schema for prompt
    schema_str = ""
    for table, columns in schema.items():
        col_list = [f"{col['column']} ({col['type']})" for col in columns]
        schema_str += f"Table: {table}\nColumns: {', '.join(col_list)}\n\n"
    
    prompt = f"""You are a SQL expert. Generate a PostgreSQL query for this question.
    
DATABASE SCHEMA:
{schema_str}

IMPORTANT FACTS:
- sow_drops table has 23,707 drop records (customer connections)
- sow_poles table has 4,471 pole records
- projects table contains project information
- For "drops" questions, use sow_drops table, NOT project_drops
- For "poles" questions, use sow_poles table

USER QUESTION: {question}

Return ONLY the SQL query, no explanations.
"""
    
    response = gemini_model.generate_content(prompt)
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    return sql

@app.get("/")
async def root():
    """Health check"""
    return {"message": "FF_Agent API is running", "status": "healthy"}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute natural language query"""
    try:
        # Generate SQL
        sql = generate_sql(request.question)
        
        # Execute query with fresh connection
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            # Fetch results
            rows = result.fetchall()
            columns = result.keys() if rows else []
            
            # Convert to list of dicts
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
            
            # Handle special types
            for item in data:
                for key, value in item.items():
                    if hasattr(value, 'isoformat'):
                        item[key] = value.isoformat()
                    elif isinstance(value, (bytes, bytearray)):
                        item[key] = str(value)
            
            return QueryResponse(
                success=True,
                question=request.question,
                sql=sql,
                data=data,
                row_count=len(data)
            )
            
    except Exception as e:
        return QueryResponse(
            success=False,
            question=request.question,
            sql=sql if 'sql' in locals() else None,
            error=str(e)
        )

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        with engine.connect() as conn:
            # Get table counts
            result = conn.execute(text("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE columns.table_name = tables.table_name) as column_count
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            tables = {}
            for row in result:
                tables[row[0]] = row[1]
            
            return {
                "status": "connected",
                "tables": tables,
                "total_tables": len(tables)
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FF_Agent API with connection pooling...")
    uvicorn.run(app, host="0.0.0.0", port=8000)