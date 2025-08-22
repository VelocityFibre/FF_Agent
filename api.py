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
from firebase_optimizer import FirebaseQueryOptimizer

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
    
    Key facts about SQL (Neon PostgreSQL):
    - projects table has project details (LAW001 = Lawley)
    - sow_drops has 23,707 customer drops
    - sow_poles has 4,471 poles
    - nokia_data has equipment records
    - status_changes has history
    
    IMPORTANT: The following data is in Firebase (NOT in SQL):
    
    PEOPLE & USERS:
    - staff: Employee records (name, role, phone, availability)
    - users: System users (uid, displayName, userGroup)
    - contractors: Contractor details (capabilities, regions, contacts)
    - clients: Client organizations
    - suppliers: Supplier information
    
    FIELD OPERATIONS:
    - field-pole-installations: Field installation data
    - pole-plantings-staging: Pole planting progress
    - staging-field-captures: Field capture data
    - uploaded-images: Field photos
    
    PROJECT MANAGEMENT:
    - projects: Project details (in Firebase, more detailed than SQL)
    - phases: Project phases
    - steps: Project steps
    - tasks: Task management
    - meetings: Meeting records (dateTime, title, organizer, insights, summary, participants, actionItems)
    - actionItemsManagement: Action items
    
    INFRASTRUCTURE (Firebase versions):
    - drops: Drop details (Firebase version)
    - planned-poles: Planned pole locations
    - pole-trackers: Pole tracking data
    
    OTHER:
    - boqItems: Bill of quantities
    - audit-logs: System audit trail
    - onemap-*: OneMap related data
    
    ROUTING RULES:
    - For staff/employee/personnel queries → "FIREBASE_QUERY: staff"
    - For user accounts → "FIREBASE_QUERY: users"
    - For contractors → "FIREBASE_QUERY: contractors"
    - For field installations → "FIREBASE_QUERY: field-pole-installations"
    - For ANY meeting queries (single meeting, meetings, insights, recent, etc.) → "FIREBASE_QUERY: meetings"
    - For tasks → "FIREBASE_QUERY: tasks"
    - For action items → "FIREBASE_QUERY: actionItemsManagement"
    - For infrastructure (drops/poles) → Use SQL unless specifically about planning
    - Default → Use SQL
    
    IMPORTANT: 
    - "what was the most recent meeting" → "FIREBASE_QUERY: meetings"
    - "latest meeting" → "FIREBASE_QUERY: meetings"
    - "show me meetings" → "FIREBASE_QUERY: meetings"
    
    Question: {question}
    
    Return ONLY the SQL query or FIREBASE_QUERY. Limit to 100 rows.
    """
    
    response = gemini_model.generate_content(prompt)
    sql = response.text.strip()
    sql = sql.replace('```sql', '').replace('```', '').strip()
    
    # Remove trailing semicolon if present
    sql = sql.rstrip(';')
    
    # Don't add LIMIT if it's a Firebase query
    if 'FIREBASE_QUERY' not in sql:
        if 'LIMIT' not in sql.upper() and 'COUNT' not in sql.upper():
            sql += ' LIMIT 100'
    
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
        
        # Check if this is a Firebase query
        if "FIREBASE_QUERY:" in sql:
            # Extract collection name
            collection = sql.split("FIREBASE_QUERY:")[1].strip().split()[0]
            
            # For now, return a message about Firebase
            # In production, you'd query Firebase here
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            try:
                # Initialize Firebase if not already done
                if not firebase_admin._apps:
                    cred = credentials.Certificate('firebase-credentials.json')
                    firebase_admin.initialize_app(cred)
                
                db = firestore.client()
                optimizer = FirebaseQueryOptimizer(db)
                
                # Check if we need specific processing
                question_lower = request.question.lower()
                
                # Use optimizer for specific collections
                if collection == 'meetings':
                    # Use optimized meeting queries
                    data = optimizer.query_meetings(request.question, limit=100)
                
                # Handle other collections with appropriate ordering
                elif collection == 'tasks':
                    # Use optimized task queries
                    data = optimizer.query_tasks(request.question, limit=100)
                
                elif collection == 'actionItemsManagement':
                    # Order by createdAt for action items
                    query = db.collection(collection)
                    query = query.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(100)
                    docs = query.stream()
                    
                    data = []
                    for doc in docs:
                        doc_data = doc.to_dict()
                        doc_data['id'] = doc.id
                        data.append(doc_data)
                
                elif collection in ['field-pole-installations', 'pole-plantings-staging', 'staging-field-captures']:
                    # Use optimized field operations queries
                    data = optimizer.query_field_operations(collection, request.question, limit=100)
                
                else:
                    # Default query for other collections
                    query = db.collection(collection)
                    query = query.limit(100)
                    docs = query.stream()
                    
                    data = []
                    for doc in docs:
                        doc_data = doc.to_dict()
                        doc_data['id'] = doc.id
                        data.append(doc_data)
                    
                    # Special handling for date queries (generic)
                    if 'recent' in question_lower or 'latest' in question_lower or 'newest' in question_lower:
                        if 'date' in question_lower or 'when' in question_lower:
                            # Sort by date field if it exists
                            date_fields = ['dateTime', 'createdAt', 'updatedAt', 'date', 'timestamp']
                            for field in date_fields:
                                if data and field in data[0]:
                                    # Sort by date
                                    sorted_data = sorted(data, key=lambda x: x.get(field, ''), reverse=True)
                                    if sorted_data:
                                        most_recent = sorted_data[0]
                                        date_value = most_recent.get(field, 'No date found')
                                        # Return just the relevant info
                                        data = [{
                                            'most_recent_date': date_value,
                                            'title': most_recent.get('title', 'N/A'),
                                            'id': most_recent.get('id', 'N/A'),
                                            'collection': collection
                                        }]
                                        break
                
                return QueryResponse(
                    success=True,
                    question=request.question,
                    sql=f"Firebase Query: {collection} collection",
                    data=data,
                    row_count=len(data)
                )
                
            except Exception as fb_error:
                return QueryResponse(
                    success=False,
                    question=request.question,
                    error=f"Firebase error: {str(fb_error)}"
                )
        
        # Regular SQL query
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