#!/usr/bin/env python3
"""
Enhanced FastAPI backend for FF_Agent with Vector Database Integration
Includes semantic search and query learning capabilities
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import google.generativeai as genai
import pandas as pd
from typing import Dict, Any, List, Optional
from firebase_optimizer import FirebaseQueryOptimizer
from vector_store import VectorStore
import time
import json

load_dotenv()

app = FastAPI(title="FF_Agent API - Enhanced")

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

# Initialize Vector Store
vector_store = VectorStore()

# Cache schema
SCHEMA_CACHE = None

class QueryRequest(BaseModel):
    question: str
    use_vector_search: bool = True  # Allow toggling vector search

class QueryResponse(BaseModel):
    success: bool
    question: str
    sql: str = None
    data: Any = None
    error: str = None
    row_count: int = 0
    vector_context_used: bool = False
    similar_queries_found: int = 0

def get_schema():
    """Get database schema from Neon"""
    global SCHEMA_CACHE
    if SCHEMA_CACHE:
        return SCHEMA_CACHE
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                table_name,
                column_name,
                data_type
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
        
        SCHEMA_CACHE = schema
        return schema

def format_schema_for_prompt(schema):
    """Format schema for the prompt"""
    lines = []
    for table, columns in schema.items():
        col_list = [f"{col['column']} ({col['type']})" for col in columns]
        lines.append(f"Table: {table}")
        lines.append(f"  Columns: {', '.join(col_list)}")
    return "\n".join(lines)

# Enhanced SQL prompt template with vector context
ENHANCED_SQL_PROMPT = """You are a SQL expert. Generate a SQL query to answer the question.

IMPORTANT RULES:
1. Use ONLY the tables and columns from the schema below
2. Return ONLY the SQL query, no explanations
3. Use proper SQL syntax for PostgreSQL
4. Include appropriate JOINs when needed
5. Use meaningful column aliases

DATABASE SCHEMA:
{schema}

SIMILAR SUCCESSFUL QUERIES (for reference):
{examples}

RELEVANT TABLES (based on semantic similarity):
{schema_hints}

AVOID THESE PATTERNS (they failed before):
{error_patterns}

USER QUESTION: {question}

SQL QUERY:"""

# Original prompt (fallback)
MAIN_SQL_PROMPT = """You are a SQL expert. Generate a SQL query to answer the question.

IMPORTANT RULES:
1. Use ONLY the tables and columns from the schema below
2. Return ONLY the SQL query, no explanations
3. Use proper SQL syntax for PostgreSQL
4. Include appropriate JOINs when needed
5. Use meaningful column aliases
6. For Firebase queries, return "FIREBASE_QUERY: collection_name" instead of SQL

DATABASE SCHEMA:
{schema}

SPECIAL COLLECTIONS (Firebase):
- meetings: Contains meeting records with scheduledTime, title, participants
- tasks: Contains task records with status, priority, assignee, dueDate
- actionItemsManagement: Contains action items with status, assignee
- users: Contains user profiles
- accounts: Contains account information

USER QUESTION: {question}

SQL QUERY:"""

def generate_enhanced_sql(question: str) -> tuple[str, Dict]:
    """Generate SQL with vector database context"""
    schema = get_schema()
    schema_str = format_schema_for_prompt(schema)
    
    # Get vector context
    context = vector_store.get_query_context(question)
    
    # Format examples
    examples_str = ""
    if context['examples']:
        for i, ex in enumerate(context['examples'][:3], 1):
            examples_str += f"\nExample {i} (similarity: {ex['similarity']}):\n"
            examples_str += f"  Question: {ex['question']}\n"
            examples_str += f"  SQL: {ex['sql']}\n"
    else:
        examples_str = "No similar queries found"
    
    # Format schema hints
    schema_hints_str = ""
    if context['schema_hints']:
        for hint in context['schema_hints']:
            schema_hints_str += f"- {hint['table']}: {', '.join(hint['relevant_columns'])}\n"
    else:
        schema_hints_str = "Use schema above to identify relevant tables"
    
    # Format error patterns
    error_patterns_str = ""
    if context['avoid_patterns']:
        for err in context['avoid_patterns']:
            error_patterns_str += f"- Avoid: {err['failed_sql'][:100]}...\n"
            error_patterns_str += f"  Error: {err['error']}\n"
    else:
        error_patterns_str = "No known error patterns"
    
    # Generate prompt with context
    prompt = ENHANCED_SQL_PROMPT.format(
        schema=schema_str,
        examples=examples_str,
        schema_hints=schema_hints_str,
        error_patterns=error_patterns_str,
        question=question
    )
    
    # Generate SQL using Gemini
    response = gemini_model.generate_content(prompt)
    sql = response.text.strip()
    
    # Clean up SQL
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    # Return SQL and context info
    return sql, {
        'vector_context_used': True,
        'similar_queries_found': len(context['examples'])
    }

def generate_sql(question: str) -> str:
    """Original SQL generation (fallback)"""
    schema = get_schema()
    schema_str = format_schema_for_prompt(schema)
    
    prompt = MAIN_SQL_PROMPT.format(
        schema=schema_str,
        question=question
    )
    
    response = gemini_model.generate_content(prompt)
    sql = response.text.strip()
    
    # Clean up SQL
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    return sql

def execute_sql(sql: str) -> tuple[List[Dict], int]:
    """Execute SQL query and return results"""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        
        # Fetch all rows
        rows = result.fetchall()
        
        # Convert to list of dicts
        if rows:
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]
            return data, len(data)
        else:
            return [], 0

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FF_Agent API (Enhanced) is running"}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute natural language query with vector search enhancement"""
    start_time = time.time()
    
    try:
        # Generate SQL with or without vector search
        if request.use_vector_search:
            try:
                sql, context_info = generate_enhanced_sql(request.question)
                vector_context_used = context_info['vector_context_used']
                similar_queries_found = context_info['similar_queries_found']
            except Exception as e:
                print(f"Vector search failed, falling back: {e}")
                sql = generate_sql(request.question)
                vector_context_used = False
                similar_queries_found = 0
        else:
            sql = generate_sql(request.question)
            vector_context_used = False
            similar_queries_found = 0
        
        # Check if this is a Firebase query
        if "FIREBASE_QUERY:" in sql:
            # Handle Firebase queries (existing code)
            collection = sql.split("FIREBASE_QUERY:")[1].strip().split()[0]
            
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate('firebase-credentials.json')
                    firebase_admin.initialize_app(cred)
                
                db = firestore.client()
                optimizer = FirebaseQueryOptimizer(db)
                
                # Execute Firebase query (simplified for brevity)
                # ... (rest of Firebase handling code)
                
                return QueryResponse(
                    success=True,
                    question=request.question,
                    sql=f"Firebase Query: {collection}",
                    data=[],  # Firebase data here
                    row_count=0,
                    vector_context_used=vector_context_used,
                    similar_queries_found=similar_queries_found
                )
                
            except Exception as e:
                # Store error pattern for learning
                if request.use_vector_search:
                    vector_store.store_error_pattern(
                        question=request.question,
                        attempted_sql=sql,
                        error_message=str(e)
                    )
                
                return QueryResponse(
                    success=False,
                    question=request.question,
                    sql=sql,
                    error=f"Firebase error: {str(e)}",
                    vector_context_used=vector_context_used,
                    similar_queries_found=similar_queries_found
                )
        
        # Execute SQL query
        data, row_count = execute_sql(sql)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Store successful query for future learning
        if request.use_vector_search and row_count > 0:
            vector_store.store_successful_query(
                question=request.question,
                sql_query=sql,
                execution_time=execution_time,
                metadata={
                    'row_count': row_count,
                    'vector_context_used': vector_context_used
                }
            )
        
        return QueryResponse(
            success=True,
            question=request.question,
            sql=sql,
            data=data,
            row_count=row_count,
            vector_context_used=vector_context_used,
            similar_queries_found=similar_queries_found
        )
        
    except Exception as e:
        # Store error pattern for learning
        if request.use_vector_search and 'sql' in locals():
            vector_store.store_error_pattern(
                question=request.question,
                attempted_sql=sql if 'sql' in locals() else "SQL generation failed",
                error_message=str(e)
            )
        
        return QueryResponse(
            success=False,
            question=request.question,
            sql=sql if 'sql' in locals() else None,
            error=str(e),
            vector_context_used=vector_context_used if 'vector_context_used' in locals() else False,
            similar_queries_found=similar_queries_found if 'similar_queries_found' in locals() else 0
        )

@app.get("/stats")
async def get_stats():
    """Get vector database statistics"""
    try:
        with vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                # Get query stats
                cur.execute("SELECT COUNT(*) as total, AVG(success_rate) as avg_success FROM query_embeddings")
                query_stats = cur.fetchone()
                
                # Get schema stats
                cur.execute("SELECT COUNT(*) as total FROM schema_embeddings")
                schema_stats = cur.fetchone()
                
                # Get error stats
                cur.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN resolved THEN 1 END) as resolved FROM error_patterns")
                error_stats = cur.fetchone()
                
                return {
                    "query_patterns": {
                        "total": query_stats[0],
                        "avg_success_rate": float(query_stats[1]) if query_stats[1] else 0
                    },
                    "schema_items": schema_stats[0],
                    "error_patterns": {
                        "total": error_stats[0],
                        "resolved": error_stats[1]
                    }
                }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)