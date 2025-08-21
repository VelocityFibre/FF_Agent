"""
Vector Database Integration for FF_Agent
Handles embeddings, similarity search, and query learning
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from dotenv import load_dotenv

load_dotenv()

class VectorStore:
    def __init__(self):
        self.neon_conn_string = os.getenv('NEON_CONNECTION_STRING')
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = "text-embedding-ada-002"  # Better for SQL/technical content
        self.embedding_dimension = 1536
        
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(self.neon_conn_string)
    
    def initialize_pgvector(self):
        """Set up pgvector extension and tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Query embeddings table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS query_embeddings (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        sql_query TEXT NOT NULL,
                        embedding vector(%s),
                        success_rate FLOAT DEFAULT 1.0,
                        execution_count INTEGER DEFAULT 1,
                        avg_execution_time FLOAT,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """, (self.embedding_dimension,))
                
                # Schema embeddings table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_embeddings (
                        id SERIAL PRIMARY KEY,
                        table_name TEXT NOT NULL,
                        column_name TEXT,
                        description TEXT,
                        embedding vector(%s),
                        usage_frequency INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """, (self.embedding_dimension,))
                
                # Error patterns table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS error_patterns (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        attempted_sql TEXT,
                        error_message TEXT,
                        embedding vector(%s),
                        occurrence_count INTEGER DEFAULT 1,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolution_sql TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """, (self.embedding_dimension,))
                
                # Create indexes for faster similarity search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS query_embedding_idx 
                    ON query_embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS schema_embedding_idx 
                    ON schema_embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 50);
                """)
                
                conn.commit()
                print("✅ pgvector initialized successfully")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def find_similar_queries(self, question: str, limit: int = 3) -> List[Dict]:
        """Find similar past queries using vector similarity"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        question,
                        sql_query,
                        success_rate,
                        execution_count,
                        avg_execution_time,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM query_embeddings
                    WHERE success_rate > 0.7
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, embedding, limit))
                
                results = cur.fetchall()
                return results
    
    def find_relevant_schema(self, question: str, limit: int = 5) -> List[Dict]:
        """Find relevant tables and columns based on semantic similarity"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        table_name,
                        column_name,
                        description,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM schema_embeddings
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, embedding, limit))
                
                results = cur.fetchall()
                return results
    
    def store_successful_query(self, question: str, sql_query: str, 
                             execution_time: float = None, metadata: Dict = None):
        """Store a successful query for future reference"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if similar query exists
                cur.execute("""
                    SELECT id, execution_count, avg_execution_time
                    FROM query_embeddings
                    WHERE sql_query = %s
                """, (sql_query,))
                
                existing = cur.fetchone()
                
                if existing:
                    # Update existing query stats
                    query_id, count, avg_time = existing
                    new_count = count + 1
                    new_avg_time = avg_time if not execution_time else \
                                   (avg_time * count + execution_time) / new_count
                    
                    cur.execute("""
                        UPDATE query_embeddings
                        SET execution_count = %s,
                            avg_execution_time = %s,
                            last_used = CURRENT_TIMESTAMP,
                            success_rate = LEAST(success_rate + 0.01, 1.0)
                        WHERE id = %s
                    """, (new_count, new_avg_time, query_id))
                else:
                    # Insert new query
                    cur.execute("""
                        INSERT INTO query_embeddings 
                        (question, sql_query, embedding, avg_execution_time, metadata)
                        VALUES (%s, %s, %s::vector, %s, %s)
                    """, (question, sql_query, embedding, execution_time, 
                          json.dumps(metadata) if metadata else None))
                
                conn.commit()
    
    def store_error_pattern(self, question: str, attempted_sql: str, error_message: str):
        """Store failed query patterns for learning"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if similar error exists
                cur.execute("""
                    SELECT id, occurrence_count
                    FROM error_patterns
                    WHERE attempted_sql = %s AND error_message LIKE %s
                """, (attempted_sql, f"%{error_message[:100]}%"))
                
                existing = cur.fetchone()
                
                if existing:
                    # Update occurrence count
                    cur.execute("""
                        UPDATE error_patterns
                        SET occurrence_count = occurrence_count + 1
                        WHERE id = %s
                    """, (existing[0],))
                else:
                    # Insert new error pattern
                    cur.execute("""
                        INSERT INTO error_patterns 
                        (question, attempted_sql, error_message, embedding)
                        VALUES (%s, %s, %s, %s::vector)
                    """, (question, attempted_sql, error_message, embedding))
                
                conn.commit()
    
    def get_error_patterns(self, question: str, limit: int = 2) -> List[Dict]:
        """Get similar error patterns to avoid repeating mistakes"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        question,
                        attempted_sql,
                        error_message,
                        resolution_sql,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM error_patterns
                    WHERE resolved = FALSE
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, embedding, limit))
                
                results = cur.fetchall()
                return results
    
    def index_schema(self, schema_definitions: List[Dict]):
        """Index database schema for semantic search"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for item in schema_definitions:
                    table_name = item.get('table_name')
                    column_name = item.get('column_name')
                    description = item.get('description', '')
                    
                    # Generate embedding for description
                    text_to_embed = f"{table_name} {column_name} {description}"
                    embedding = self.generate_embedding(text_to_embed)
                    
                    if embedding:
                        cur.execute("""
                            INSERT INTO schema_embeddings 
                            (table_name, column_name, description, embedding)
                            VALUES (%s, %s, %s, %s::vector)
                            ON CONFLICT DO NOTHING
                        """, (table_name, column_name, description, embedding))
                
                conn.commit()
                print(f"✅ Indexed {len(schema_definitions)} schema items")
    
    def get_query_context(self, question: str) -> Dict:
        """Get comprehensive context for SQL generation"""
        context = {
            'similar_queries': self.find_similar_queries(question),
            'relevant_schema': self.find_relevant_schema(question),
            'error_patterns': self.get_error_patterns(question)
        }
        
        # Format for prompt
        formatted_context = {
            'examples': [],
            'schema_hints': [],
            'avoid_patterns': []
        }
        
        # Format similar queries as examples
        for q in context['similar_queries']:
            formatted_context['examples'].append({
                'question': q['question'],
                'sql': q['sql_query'],
                'similarity': f"{q['similarity']:.2f}",
                'success_rate': f"{q['success_rate']:.2f}"
            })
        
        # Format schema hints
        schema_by_table = {}
        for s in context['relevant_schema']:
            table = s['table_name']
            if table not in schema_by_table:
                schema_by_table[table] = []
            if s['column_name']:
                schema_by_table[table].append(s['column_name'])
        
        for table, columns in schema_by_table.items():
            formatted_context['schema_hints'].append({
                'table': table,
                'relevant_columns': columns
            })
        
        # Format error patterns to avoid
        for e in context['error_patterns']:
            formatted_context['avoid_patterns'].append({
                'similar_question': e['question'],
                'failed_sql': e['attempted_sql'],
                'error': e['error_message'][:100]
            })
        
        return formatted_context