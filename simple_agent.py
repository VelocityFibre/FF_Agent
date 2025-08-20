#!/usr/bin/env python3
"""
Simple FF_Agent - Direct SQL with Gemini
No complex agent chains, just:
1. Gemini generates SQL from your question
2. Execute SQL directly
3. Return results
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import google.generativeai as genai
import pandas as pd
import json

load_dotenv()

class SimpleFFAgent:
    def __init__(self):
        # Setup Gemini
        genai.configure(api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Setup database
        self.engine = create_engine(os.getenv("NEON_DATABASE_URL"))
        
        # Get schema once
        self.schema = self._get_schema()
    
    def _get_schema(self):
        """Get database schema"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """))
            
            schema = {}
            for row in result:
                table, column, dtype = row
                if table not in schema:
                    schema[table] = []
                schema[table].append(f"{column} ({dtype})")
            
            return schema
    
    def query(self, question):
        """Convert question to SQL and execute"""
        
        # Build context
        schema_context = "Database tables:\n"
        for table, columns in list(self.schema.items())[:10]:  # Limit to key tables
            if table in ['projects', 'sow_drops', 'sow_poles', 'nokia_data', 'status_changes']:
                schema_context += f"\n{table}:\n"
                for col in columns[:8]:  # Show first 8 columns
                    schema_context += f"  - {col}\n"
        
        # Generate SQL
        prompt = f"""
        You are a SQL expert. Generate a PostgreSQL query for this question.
        
        {schema_context}
        
        Question: {question}
        
        Return ONLY the SQL query, no explanation. 
        Limit results to 100 rows.
        """
        
        try:
            response = self.model.generate_content(prompt)
            sql = response.text.strip()
            
            # Clean SQL
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            print(f"Generated SQL: {sql[:200]}...")
            
            # Execute
            with self.engine.connect() as conn:
                result = pd.read_sql_query(sql, conn)
                
                return {
                    "success": True,
                    "data": result.to_dict('records'),
                    "sql": sql,
                    "row_count": len(result)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def test_simple_agent():
    agent = SimpleFFAgent()
    
    test_questions = [
        "How many drops are in the Lawley project?",
        "Show me all projects",
        "What is the total count of poles?",
        "Show top 5 poles with most drops"
    ]
    
    for q in test_questions:
        print(f"\n❓ {q}")
        result = agent.query(q)
        if result["success"]:
            print(f"✅ Found {result['row_count']} rows")
            if result['data']:
                print(json.dumps(result['data'][:2], indent=2))  # Show first 2 rows
        else:
            print(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    test_simple_agent()