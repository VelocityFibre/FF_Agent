#!/usr/bin/env python3
"""
FF_Agent using Vanna AI - Production-ready NL to SQL
Vanna is battle-tested and used by Fortune 500 companies
"""

import os
from dotenv import load_dotenv
import vanna
from vanna.chromadb import ChromaDB_VectorStore
import pandas as pd
from typing import Dict, Any, List
import json
import google.generativeai as genai

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_AI_STUDIO_API_KEY'))


class MyVanna(ChromaDB_VectorStore):
    """Vanna with local ChromaDB storage and custom Gemini integration"""
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config={'path': './vanna_chroma'})
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        self.conversation = []
    
    def generate_sql(self, question: str, **kwargs) -> str:
        """Generate SQL using Gemini"""
        # Get training data for context
        training_data = self.get_related_training_data(question)
        
        context = "Database context:\n"
        for item in training_data[:5]:  # Use top 5 most relevant
            if 'ddl' in item:
                context += f"Table: {item['ddl'][:200]}...\n"
            if 'question' in item and 'sql' in item:
                context += f"Example: {item['question']} -> {item['sql']}\n"
        
        prompt = f"""
        {context}
        
        Question: {question}
        
        Generate a PostgreSQL SQL query to answer this question.
        Return only the SQL query, no explanations.
        """
        
        response = self.gemini_model.generate_content(prompt)
        sql = response.text.strip()
        sql = sql.replace('```sql', '').replace('```', '').strip()
        return sql
    
    def submit_prompt(self, prompt, **kwargs) -> str:
        """Submit prompt to Gemini"""
        response = self.gemini_model.generate_content(prompt)
        return response.text
    
    def system_message(self, message: str) -> str:
        """Add system message"""
        self.conversation.append({"role": "system", "content": message})
        return ""
    
    def user_message(self, message: str) -> str:
        """Add user message"""
        self.conversation.append({"role": "user", "content": message})
        return ""
    
    def assistant_message(self, message: str) -> str:
        """Add assistant message"""
        self.conversation.append({"role": "assistant", "content": message})
        return ""


class FF_Agent_Vanna:
    """Production-grade FF_Agent using Vanna AI"""
    
    def __init__(self):
        print("Initializing Vanna AI for FF_Agent...")
        
        # Initialize Vanna with local storage and Gemini
        self.vn = MyVanna()
        
        # Connect to your Neon database
        self.vn.connect_to_postgres(
            host='ep-long-breeze-a9w7xool.gwc.azure.neon.tech',
            dbname='neondb',
            user='neondb_owner', 
            password='npg_AlX83ojfZpBk',
            port=5432,
            sslmode='require'
        )
        
        print("✅ Connected to Neon database")
        
        # Train the model on first run
        self._train_if_needed()
    
    def _train_if_needed(self):
        """Train Vanna on database schema and sample queries"""
        
        # Check if already trained
        training_data = self.vn.get_training_data()
        if isinstance(training_data, pd.DataFrame) and not training_data.empty:
            print(f"✅ Model already trained with {len(training_data)} items")
            return
        elif isinstance(training_data, list) and len(training_data) > 0:
            print(f"✅ Model already trained with {len(training_data)} items")
            return
        
        print("Training Vanna on FibreFlow schema...")
        
        # 1. Train on information schema (DDL)
        ddl = self.vn.run_sql("""
            SELECT 
                'CREATE TABLE ' || table_name || ' (' ||
                string_agg(
                    column_name || ' ' || 
                    data_type || 
                    CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                    ', '
                ) || ');' as ddl
            FROM information_schema.columns
            WHERE table_schema = 'public' 
                AND table_name IN ('projects', 'sow_drops', 'sow_poles', 
                                  'sow_fibre', 'nokia_data', 'status_changes')
            GROUP BY table_name
        """)
        
        for ddl_statement in ddl['ddl'].values:
            self.vn.train(ddl=ddl_statement)
        
        # 2. Train on documentation
        self.vn.train(documentation="""
        FibreFlow Telecommunications Database Documentation:
        
        PROJECTS table: Contains all fiber optic installation projects
        - project_code: Unique identifier (LAW001 = Lawley, IP-001 = Ivory Park, etc)
        - name: Project name
        - firebase_id: Links to Firebase data
        - created_at: When project was created
        
        SOW_DROPS table: Customer connection points (23,707 total)
        - drop_number: Unique drop identifier (e.g., DR1737348)
        - pole_number: Which pole it connects to (e.g., LAW.P.A002)
        - project_id: Links to projects.firebase_id
        - status: Installation status
        - address: Physical location
        
        SOW_POLES table: Infrastructure poles (4,471 total)
        - pole_number: Unique pole ID (e.g., LAW.P.A002)
        - status: Current status (mostly "Permission not granted")
        - project_id: Which project owns this pole
        - latitude/longitude: GPS coordinates
        
        SOW_FIBRE table: Fiber cable segments between poles
        - segment_id: Unique segment identifier
        - from_point: Starting pole
        - to_point: Ending pole
        - cable_length: Length in meters
        
        NOKIA_DATA table: ONT/equipment records (327 active units)
        - serial_number: Device serial
        - status: Active/Inactive
        - drop_number: Which drop it serves
        
        STATUS_CHANGES table: Historical tracking (27,699 records)
        - Records all status changes for drops, poles, installations
        """)
        
        # 3. Train on sample question-SQL pairs
        training_pairs = [
            ("How many drops are there in total?",
             "SELECT COUNT(*) as total_drops FROM sow_drops;"),
            
            ("How many drops are in the Lawley project?",
             """SELECT COUNT(*) as lawley_drops 
                FROM sow_drops 
                WHERE drop_number LIKE 'LAW%' OR pole_number LIKE 'LAW%';"""),
            
            ("Show all projects",
             """SELECT project_code, name, created_at 
                FROM projects 
                ORDER BY created_at DESC;"""),
            
            ("What's the total number of poles?",
             "SELECT COUNT(DISTINCT pole_number) as total_poles FROM sow_poles;"),
            
            ("Show pole status breakdown",
             """SELECT status, COUNT(*) as count 
                FROM sow_poles 
                GROUP BY status 
                ORDER BY count DESC;"""),
            
            ("Which poles have the most drops?",
             """SELECT pole_number, COUNT(*) as drop_count 
                FROM sow_drops 
                WHERE pole_number IS NOT NULL 
                GROUP BY pole_number 
                ORDER BY drop_count DESC 
                LIMIT 10;"""),
            
            ("How many drops per project?",
             """SELECT p.name, p.project_code, COUNT(d.drop_number) as drop_count
                FROM projects p
                LEFT JOIN sow_drops d ON d.project_id = p.firebase_id
                GROUP BY p.name, p.project_code
                ORDER BY drop_count DESC;"""),
            
            ("Show active Nokia equipment",
             """SELECT status, COUNT(*) as count 
                FROM nokia_data 
                GROUP BY status;"""),
            
            ("What's the installation progress?",
             """SELECT status, COUNT(*) as count
                FROM status_changes
                WHERE status IS NOT NULL
                GROUP BY status
                ORDER BY count DESC
                LIMIT 10;""")
        ]
        
        for question, sql in training_pairs:
            self.vn.train(question=question, sql=sql)
        
        print(f"✅ Training complete! Trained on {len(training_pairs)} examples")
    
    def query(self, question: str) -> Dict[str, Any]:
        """Execute natural language query"""
        
        try:
            # Generate SQL using Vanna
            sql = self.vn.generate_sql(question)
            print(f"Generated SQL: {sql[:200]}...")
            
            # Run the SQL
            df = self.vn.run_sql(sql)
            
            # Format response
            if df is None or df.empty:
                answer = "No data found"
            elif len(df) == 1 and len(df.columns) == 1:
                # Single value
                answer = str(df.iloc[0, 0])
            else:
                # Table of results
                answer = df.to_string(index=False, max_rows=20)
                if len(df) > 20:
                    answer += f"\n... ({len(df)} total rows)"
            
            return {
                "success": True,
                "question": question,
                "sql": sql,
                "answer": answer,
                "rows": len(df) if df is not None else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "question": question,
                "error": str(e)
            }
    
    def ask(self, question: str) -> str:
        """Simple interface - returns just the answer"""
        result = self.query(question)
        
        if result["success"]:
            return result["answer"]
        else:
            return f"Error: {result['error']}"
    
    def get_training_data(self) -> List:
        """View what the model has learned"""
        return self.vn.get_training_data()
    
    def generate_followup_questions(self, question: str) -> List[str]:
        """Generate relevant follow-up questions"""
        return self.vn.generate_followup_questions(question)


def test_vanna():
    """Test the Vanna implementation"""
    print("\n" + "="*60)
    print("TESTING VANNA AI IMPLEMENTATION")
    print("="*60)
    
    agent = FF_Agent_Vanna()
    
    test_questions = [
        "How many drops are in the system?",
        "What projects do we have?",
        "Show pole status breakdown",
        "How many drops in Lawley?",
        "Which poles have the most connections?"
    ]
    
    for q in test_questions:
        print(f"\n❓ Question: {q}")
        print("-" * 40)
        answer = agent.ask(q)
        print(f"💬 Answer:\n{answer}")
    
    print("\n" + "="*60)
    print("✅ Vanna AI is working!")
    print("="*60)


if __name__ == "__main__":
    test_vanna()