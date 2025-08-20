#!/usr/bin/env python3
"""
FastAPI backend for FF_Agent
Simple API that uses direct SQL queries
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import google.generativeai as genai
import pandas as pd
from typing import Dict, Any, List

load_dotenv()

app = FastAPI(title="FF_Agent API")

# Enable CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Database connection
engine = create_engine(os.getenv("NEON_DATABASE_URL"))

# Cache schema
SCHEMA_CACHE = None

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
    """Get database schema (cached)"""
    global SCHEMA_CACHE
    if SCHEMA_CACHE:
        return SCHEMA_CACHE
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
                AND table_name IN ('projects', 'sow_drops', 'sow_poles', 
                                  'sow_fibre', 'nokia_data', 'status_changes')
            ORDER BY table_name, ordinal_position
        """))
        
        schema = {}
        for row in result:
            table, column, dtype = row
            if table not in schema:
                schema[table] = []
            schema[table].append(f"{column} ({dtype})")
        
        SCHEMA_CACHE = schema
        return schema

def generate_sql(question: str) -> str:
    """Generate SQL from natural language"""
    schema = get_schema()
    
    schema_text = "Database schema:\n"
    for table, columns in schema.items():
        schema_text += f"\n{table}:\n"
        for col in columns[:8]:  # First 8 columns
            schema_text += f"  - {col}\n"
    
    prompt = f"""
    You are a SQL expert. Generate PostgreSQL for this question.
    
    {schema_text}
    
    Key facts:
    - projects table has project details (LAW001 = Lawley)
    - sow_drops has 23,707 customer drops
    - sow_poles has 4,471 poles
    - Most data is for Lawley project
    
    Question: {question}
    
    Return ONLY the SQL query. Limit to 100 rows.
    """
    
    response = gemini_model.generate_content(prompt)
    sql = response.text.strip()
    sql = sql.replace('```sql', '').replace('```', '').strip()
    
    if 'LIMIT' not in sql.upper() and 'COUNT' not in sql.upper():
        sql += '\nLIMIT 100'
    
    return sql

@app.get("/")
def root():
    return {"message": "FF_Agent API is running"}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute natural language query"""
    try:
        # Generate SQL
        sql = generate_sql(request.question)
        
        # Execute SQL
        with engine.connect() as conn:
            result = pd.read_sql_query(sql, conn)
        
        # Format response
        if result.empty:
            data = "No data found"
        else:
            data = result.to_dict('records')
        
        return QueryResponse(
            success=True,
            question=request.question,
            sql=sql,
            data=data,
            row_count=len(result)
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            question=request.question,
            error=str(e)
        )

@app.get("/schema")
def get_schema_endpoint():
    """Get database schema"""
    return get_schema()

@app.get("/stats")
def get_stats():
    """Get database statistics"""
    with engine.connect() as conn:
        stats = {}
        
        # Get counts
        tables = ['projects', 'sow_drops', 'sow_poles', 'nokia_data']
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            stats[table] = result.scalar()
        
        return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)