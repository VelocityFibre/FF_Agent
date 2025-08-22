"""
FF_Agent Integrated API - Connects all components
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text, pool
from sqlalchemy.pool import NullPool
import google.generativeai as genai
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions

# Import our components
from ff_agent_vanna import FF_Agent_Vanna
from vector_store_cached import CachedVectorStore
from feedback_system import FeedbackSystem

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False
)

# Initialize Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize components
vanna_agent = None
vector_store = None
feedback_system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all components on startup"""
    global vanna_agent, vector_store, feedback_system
    
    try:
        # Initialize Vanna
        logger.info("Initializing Vanna agent...")
        vanna_agent = FF_Agent_Vanna()  # No parameters needed
        # Connection is already handled in the class initialization
        
        # Initialize Vector Store
        logger.info("Initializing Vector Store...")
        vector_store = CachedVectorStore()
        
        # Initialize Feedback System
        logger.info("Initializing Feedback System...")
        feedback_system = FeedbackSystem()
        
        logger.info("All components initialized successfully")
        yield
    finally:
        logger.info("Shutting down components...")

app = FastAPI(title="FF_Agent Integrated API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class QueryRequest(BaseModel):
    question: str
    use_vector_search: bool = True
    use_vanna: bool = True
    confidence_threshold: float = 0.7

class QueryResponse(BaseModel):
    success: bool
    question: str
    sql: Optional[str] = None
    data: Optional[List[Dict]] = None
    error: Optional[str] = None
    row_count: Optional[int] = None
    method_used: Optional[str] = None
    confidence: Optional[float] = None
    similar_patterns: Optional[List[Dict]] = None

class FeedbackRequest(BaseModel):
    query_id: str
    question: str
    sql: str
    was_correct: bool
    feedback: Optional[str] = None
    corrected_sql: Optional[str] = None

class SuggestionRequest(BaseModel):
    partial_query: str
    limit: int = 5

def get_schema() -> Dict:
    """Get database schema"""
    schema = {}
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """))
        
        for row in result:
            table_name = row[0]
            if table_name not in schema:
                schema[table_name] = []
            schema[table_name].append({
                'column': row[1],
                'type': row[2]
            })
    return schema

def generate_sql_with_context(question: str, similar_patterns: List[Dict] = None) -> tuple[str, float]:
    """Generate SQL using context from vector store"""
    schema = get_schema()
    
    # Format schema
    schema_str = ""
    for table, columns in schema.items():
        col_list = [f"{col['column']} ({col['type']})" for col in columns]
        schema_str += f"Table: {table}\nColumns: {', '.join(col_list)}\n\n"
    
    # Add similar patterns as examples
    examples_str = ""
    if similar_patterns:
        examples_str = "\nSIMILAR SUCCESSFUL QUERIES:\n"
        for pattern in similar_patterns[:3]:  # Use top 3
            examples_str += f"Question: {pattern.get('question', 'N/A')}\n"
            examples_str += f"SQL: {pattern.get('sql', 'N/A')}\n\n"
    
    prompt = f"""You are a SQL expert. Generate a PostgreSQL query for this question.
    
DATABASE SCHEMA:
{schema_str}

IMPORTANT FACTS:
- sow_drops table has 23,707 drop records (customer connections)
- sow_poles table has 4,471 pole records
- projects table contains project information
- For "drops" questions, use sow_drops table, NOT project_drops
- For "poles" questions, use sow_poles table
{examples_str}
USER QUESTION: {question}

Return ONLY the SQL query, no explanations. Also provide a confidence score (0-1) for your answer.
Format: 
SQL: <query>
CONFIDENCE: <score>
"""
    
    response = gemini_model.generate_content(prompt)
    response_text = response.text.strip()
    
    # Parse SQL and confidence
    sql = ""
    confidence = 0.5
    
    if "SQL:" in response_text and "CONFIDENCE:" in response_text:
        parts = response_text.split("CONFIDENCE:")
        sql_part = parts[0].replace("SQL:", "").strip()
        sql = sql_part.replace("```sql", "").replace("```", "").strip()
        try:
            confidence = float(parts[1].strip())
        except:
            confidence = 0.5
    else:
        sql = response_text.replace("```sql", "").replace("```", "").strip()
    
    return sql, confidence

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query using all available methods"""
    try:
        method_used = None
        sql = None
        confidence = 0.0
        similar_patterns = None
        
        # Step 1: Try Vector Store first for similar patterns
        if request.use_vector_search and vector_store:
            try:
                logger.info(f"Searching vector store for: {request.question}")
                similar_patterns = vector_store.search(request.question, top_k=5)
                
                if similar_patterns and len(similar_patterns) > 0:
                    # Check if we have a very similar pattern
                    top_match = similar_patterns[0]
                    if top_match.get('similarity', 0) > 0.9:
                        sql = top_match.get('sql')
                        confidence = top_match.get('similarity', 0)
                        method_used = "vector_exact_match"
                        logger.info(f"Found exact match in vector store with confidence {confidence}")
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")
        
        # Step 2: Try Vanna if vector didn't give high confidence
        if request.use_vanna and vanna_agent and confidence < request.confidence_threshold:
            try:
                logger.info("Trying Vanna agent...")
                # The vanna object is inside the FF_Agent_Vanna class
                vanna_sql = vanna_agent.vn.generate_sql(request.question)
                if vanna_sql:
                    sql = vanna_sql
                    confidence = 0.8  # Vanna typically has good confidence
                    method_used = "vanna"
                    logger.info("Generated SQL using Vanna")
            except Exception as e:
                logger.warning(f"Vanna generation failed: {e}")
        
        # Step 3: Fall back to Gemini with context
        if confidence < request.confidence_threshold:
            logger.info("Using Gemini with context...")
            sql, confidence = generate_sql_with_context(request.question, similar_patterns)
            method_used = "gemini_with_context" if similar_patterns else "gemini_direct"
        
        # Execute the SQL
        logger.info(f"Executing SQL: {sql}")
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result]
            
            # Convert datetime objects to strings
            for row in data:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
        
        # Store successful query in vector store
        if vector_store and confidence > 0.7:
            try:
                vector_store.add_pattern(
                    question=request.question,
                    sql=sql,
                    metadata={
                        'method': method_used,
                        'confidence': confidence,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store pattern: {e}")
        
        # Log to feedback system
        if feedback_system:
            query_id = feedback_system.log_query(
                question=request.question,
                sql=sql,
                success=True,
                method=method_used
            )
        
        return QueryResponse(
            success=True,
            question=request.question,
            sql=sql,
            data=data,
            row_count=len(data),
            method_used=method_used,
            confidence=confidence,
            similar_patterns=similar_patterns[:3] if similar_patterns else None
        )
            
    except Exception as e:
        logger.error(f"Query failed: {e}")
        
        # Log failure to feedback system
        if feedback_system:
            feedback_system.log_query(
                question=request.question,
                sql=sql if sql else None,
                success=False,
                error=str(e)
            )
        
        return QueryResponse(
            success=False,
            question=request.question,
            sql=sql if sql else None,
            error=str(e)
        )

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback for a query"""
    try:
        if feedback_system:
            feedback_system.record_feedback(
                query_id=request.query_id,
                was_correct=request.was_correct,
                feedback=request.feedback,
                corrected_sql=request.corrected_sql
            )
        
        # If corrected SQL provided, add to vector store
        if request.corrected_sql and vector_store:
            vector_store.add_pattern(
                question=request.question,
                sql=request.corrected_sql,
                metadata={
                    'source': 'user_correction',
                    'timestamp': datetime.now().isoformat()
                }
            )
        
        # Train Vanna with correction
        if request.corrected_sql and vanna_agent:
            vanna_agent.vn.train(
                question=request.question,
                sql=request.corrected_sql
            )
        
        return {"success": True, "message": "Feedback recorded"}
    
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    """Get query suggestions based on partial input"""
    try:
        suggestions = []
        
        # Get suggestions from vector store
        if vector_store:
            patterns = vector_store.search(request.partial_query, top_k=request.limit)
            suggestions = [p.get('question') for p in patterns if p.get('question')]
        
        return {"suggestions": suggestions[:request.limit]}
    
    except Exception as e:
        logger.error(f"Suggestion generation failed: {e}")
        return {"suggestions": []}

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        stats = {
            "status": "connected",
            "components": {
                "vanna": "active" if vanna_agent else "inactive",
                "vector_store": "active" if vector_store else "inactive",
                "feedback_system": "active" if feedback_system else "inactive"
            }
        }
        
        # Get database stats
        with engine.connect() as conn:
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
            
            stats["database"] = {
                "tables": tables,
                "total_tables": len(tables)
            }
        
        # Get vector store stats
        if vector_store:
            try:
                collection = vector_store.collection
                stats["vector_store"] = {
                    "total_patterns": collection.count(),
                    "status": "active"
                }
            except:
                pass
        
        # Get feedback stats
        if feedback_system:
            try:
                stats["feedback"] = feedback_system.get_stats()
            except:
                pass
        
        return stats
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "connected" if engine else "disconnected",
            "vanna": "ready" if vanna_agent else "not initialized",
            "vector_store": "ready" if vector_store else "not initialized",
            "feedback": "ready" if feedback_system else "not initialized"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FF_Agent Integrated API...")
    print("✅ Vanna AI integration enabled")
    print("✅ Vector Store with semantic search enabled")
    print("✅ Feedback system enabled")
    print("✅ Query suggestions enabled")
    uvicorn.run(app, host="0.0.0.0", port=8000)