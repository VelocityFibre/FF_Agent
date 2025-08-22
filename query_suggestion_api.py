"""
Query Suggestion API
Intelligent autocomplete and query suggestions based on learned patterns
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from vector_store_cached import CachedVectorStore

load_dotenv()

app = FastAPI(title="Query Suggestion API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuerySuggestionEngine:
    def __init__(self):
        self.conn_string = os.getenv('NEON_CONNECTION_STRING')
        self.vector_store = CachedVectorStore()
        self.patterns_cache = self._load_patterns()
        self.table_names = self._load_table_names()
        
    def get_connection(self):
        return psycopg2.connect(self.conn_string)
    
    def _load_patterns(self) -> List[Dict]:
        """Load all patterns from database"""
        patterns = []
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT question, sql_query, success_rate, execution_count
                        FROM query_embeddings
                        ORDER BY execution_count DESC, success_rate DESC
                    """)
                    patterns = cur.fetchall()
        except Exception as e:
            print(f"Error loading patterns: {e}")
        
        # Also load from JSON files
        try:
            import glob
            for json_file in glob.glob("patterns_batch_*.json"):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    for p in data.get('patterns', []):
                        patterns.append({
                            'question': p['question'],
                            'sql_query': p['sql'],
                            'success_rate': 1.0,
                            'execution_count': 0
                        })
        except Exception as e:
            print(f"Error loading JSON patterns: {e}")
        
        return patterns
    
    def _load_table_names(self) -> List[str]:
        """Get all table names from database"""
        tables = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"Error loading tables: {e}")
        return tables
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[Dict]:
        """Get query suggestions based on partial input"""
        query_lower = query.lower().strip()
        suggestions = []
        
        # If query is empty, return popular patterns
        if not query_lower:
            return self._get_popular_patterns(limit)
        
        # Score and rank all patterns
        scored_patterns = []
        
        for pattern in self.patterns_cache:
            question = pattern['question']
            question_lower = question.lower()
            
            score = 0
            
            # Exact prefix match (highest priority)
            if question_lower.startswith(query_lower):
                score += 100
            
            # Contains all query words
            query_words = query_lower.split()
            if all(word in question_lower for word in query_words):
                score += 50
            
            # Fuzzy string matching
            fuzzy_score = fuzz.partial_ratio(query_lower, question_lower)
            score += fuzzy_score * 0.5
            
            # Boost based on usage
            score += pattern.get('execution_count', 0) * 2
            score += pattern.get('success_rate', 0) * 10
            
            # Check if table name is mentioned
            for table in self.table_names:
                if table in query_lower and table in question_lower:
                    score += 30
            
            if score > 30:  # Threshold for relevance
                scored_patterns.append({
                    'question': question,
                    'sql': pattern['sql_query'],
                    'score': score,
                    'usage_count': pattern.get('execution_count', 0),
                    'success_rate': pattern.get('success_rate', 1.0)
                })
        
        # Sort by score and return top suggestions
        scored_patterns.sort(key=lambda x: x['score'], reverse=True)
        
        # Format suggestions
        for pattern in scored_patterns[:limit]:
            suggestions.append({
                'suggestion': pattern['question'],
                'sql_preview': pattern['sql'][:100] + '...' if len(pattern['sql']) > 100 else pattern['sql'],
                'confidence': min(pattern['score'] / 100, 1.0),
                'usage_count': pattern['usage_count'],
                'type': self._classify_query(pattern['question'])
            })
        
        return suggestions
    
    def _get_popular_patterns(self, limit: int) -> List[Dict]:
        """Get most popular query patterns"""
        popular = []
        
        # Group patterns by type
        basic_queries = [
            "Show all",
            "Count records",
            "Show recent",
            "Find by status",
            "Get total"
        ]
        
        for prefix in basic_queries[:limit]:
            matching = [p for p in self.patterns_cache if p['question'].lower().startswith(prefix.lower())]
            if matching:
                pattern = matching[0]
                popular.append({
                    'suggestion': pattern['question'],
                    'sql_preview': pattern['sql_query'][:100] + '...' if len(pattern['sql_query']) > 100 else pattern['sql_query'],
                    'confidence': 1.0,
                    'usage_count': pattern.get('execution_count', 0),
                    'type': self._classify_query(pattern['question'])
                })
        
        return popular
    
    def _classify_query(self, question: str) -> str:
        """Classify query type"""
        question_lower = question.lower()
        
        if 'count' in question_lower:
            return 'aggregation'
        elif 'sum' in question_lower or 'avg' in question_lower or 'total' in question_lower:
            return 'calculation'
        elif 'group by' in question_lower or 'by status' in question_lower:
            return 'grouping'
        elif 'recent' in question_lower or 'last' in question_lower or 'date' in question_lower:
            return 'temporal'
        elif 'find' in question_lower or 'search' in question_lower:
            return 'search'
        elif 'show all' in question_lower or 'list' in question_lower:
            return 'listing'
        else:
            return 'general'
    
    def get_table_suggestions(self, partial: str) -> List[str]:
        """Get table name suggestions"""
        partial_lower = partial.lower()
        return [
            table for table in self.table_names 
            if partial_lower in table.lower()
        ][:10]
    
    def get_column_suggestions(self, table_name: str) -> List[Dict]:
        """Get column suggestions for a specific table"""
        columns = []
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns = [
                        {'name': row[0], 'type': row[1]}
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            print(f"Error loading columns: {e}")
        return columns

# Initialize suggestion engine
suggestion_engine = QuerySuggestionEngine()

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Query Suggestion API",
        "version": "1.0",
        "endpoints": {
            "/suggest": "Get query suggestions",
            "/tables": "Get table name suggestions",
            "/columns/{table}": "Get column suggestions for a table",
            "/complete": "Complete partial query",
            "/examples": "Get example queries"
        }
    }

@app.get("/suggest")
async def suggest_queries(
    q: str = Query("", description="Partial query string"),
    limit: int = Query(10, description="Maximum suggestions to return")
):
    """Get query suggestions based on partial input"""
    suggestions = suggestion_engine.get_suggestions(q, limit)
    
    return {
        "query": q,
        "suggestions": suggestions,
        "count": len(suggestions)
    }

@app.get("/tables")
async def suggest_tables(
    q: str = Query("", description="Partial table name")
):
    """Get table name suggestions"""
    tables = suggestion_engine.get_table_suggestions(q)
    
    return {
        "query": q,
        "tables": tables,
        "count": len(tables)
    }

@app.get("/columns/{table_name}")
async def get_columns(table_name: str):
    """Get columns for a specific table"""
    columns = suggestion_engine.get_column_suggestions(table_name)
    
    if not columns:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    return {
        "table": table_name,
        "columns": columns,
        "count": len(columns)
    }

@app.get("/complete")
async def complete_query(
    q: str = Query(..., description="Partial query to complete")
):
    """Auto-complete a partial query with intelligent suggestions"""
    query_lower = q.lower().strip()
    
    completions = []
    
    # Detect what user is trying to write
    if query_lower.startswith("show"):
        completions = [
            f"{q} all {table}" for table in suggestion_engine.table_names[:5]
        ]
    elif query_lower.startswith("count"):
        completions = [
            f"{q} records in {table}" for table in suggestion_engine.table_names[:5]
        ]
    elif query_lower.startswith("find"):
        completions = [
            f"{q} by id",
            f"{q} by status",
            f"{q} recent records",
            f"{q} with errors",
            f"{q} active items"
        ]
    elif query_lower.startswith("get"):
        completions = [
            f"{q} total",
            f"{q} average",
            f"{q} recent",
            f"{q} by date",
            f"{q} status summary"
        ]
    else:
        # Use vector similarity for more complex completions
        suggestions = suggestion_engine.get_suggestions(q, 5)
        completions = [s['suggestion'] for s in suggestions]
    
    return {
        "query": q,
        "completions": completions[:10],
        "type": "intelligent" if completions else "none"
    }

@app.get("/examples")
async def get_example_queries(
    category: Optional[str] = Query(None, description="Query category filter")
):
    """Get example queries by category"""
    examples = {
        "basic": [
            "Show all customers",
            "Count total orders",
            "List recent imports",
            "Find active projects"
        ],
        "aggregation": [
            "Count records by status",
            "Calculate total revenue",
            "Get average response time",
            "Sum quantities by product"
        ],
        "temporal": [
            "Show data from last week",
            "Get this month's records",
            "Find recent changes",
            "List today's activities"
        ],
        "complex": [
            "Show customers with orders",
            "Find failed imports with errors",
            "Get status summary by project",
            "Calculate utilization rates"
        ]
    }
    
    if category and category in examples:
        return {
            "category": category,
            "examples": examples[category]
        }
    
    return {
        "categories": list(examples.keys()),
        "examples": examples
    }

@app.get("/stats")
async def get_stats():
    """Get suggestion engine statistics"""
    return {
        "total_patterns": len(suggestion_engine.patterns_cache),
        "total_tables": len(suggestion_engine.table_names),
        "pattern_sources": {
            "database": sum(1 for p in suggestion_engine.patterns_cache if p.get('execution_count', 0) > 0),
            "json_files": sum(1 for p in suggestion_engine.patterns_cache if p.get('execution_count', 0) == 0)
        },
        "top_patterns": [
            p['question'] for p in 
            sorted(suggestion_engine.patterns_cache, 
                   key=lambda x: x.get('execution_count', 0), 
                   reverse=True)[:5]
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Query Suggestion API on http://localhost:8002")
    print("📝 Try: http://localhost:8002/suggest?q=show")
    print("📊 Stats: http://localhost:8002/stats")
    uvicorn.run(app, host="0.0.0.0", port=8002)