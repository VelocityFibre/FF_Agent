#!/usr/bin/env python3
"""
Properly train Vanna with BOTH Neon and Firebase schemas
Using Vanna's standard training methods
"""

import os
from dotenv import load_dotenv
from vanna.chromadb import ChromaDB_VectorStore
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from sqlalchemy import create_engine, text
import json

load_dotenv()

class VannaTrainer:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=os.getenv('GOOGLE_AI_STUDIO_API_KEY'))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize Vanna
        self.vn = ChromaDB_VectorStore(config={'path': './vanna_chroma'})
        
        # Connect to Neon
        self.engine = create_engine(os.getenv("NEON_DATABASE_URL"))
        
        # Connect to Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
        self.firebase_db = firestore.client()
    
    def train_complete_system(self):
        """Train Vanna with complete knowledge of both databases"""
        
        print("="*60)
        print("TRAINING VANNA WITH COMPLETE SYSTEM KNOWLEDGE")
        print("="*60)
        
        # 1. Train on Neon SQL Schema (DDL)
        self._train_neon_schema()
        
        # 2. Train on Firebase Schema
        self._train_firebase_schema()
        
        # 3. Train on routing logic
        self._train_routing_logic()
        
        # 4. Train on example queries
        self._train_example_queries()
        
        # 5. Verify training
        self._verify_training()
        
        print("\n✅ Training complete!")
    
    def _train_neon_schema(self):
        """Train on Neon PostgreSQL schema using Vanna's add_ddl method"""
        print("\n1. Training on Neon PostgreSQL Schema...")
        
        with self.engine.connect() as conn:
            # Get all table DDLs
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            tables = conn.execute(text(tables_query))
            
            for table in tables:
                table_name = table[0]
                
                # Get CREATE TABLE statement
                ddl_query = f"""
                    SELECT 
                        'CREATE TABLE ' || table_name || ' (' ||
                        string_agg(
                            column_name || ' ' || 
                            data_type || 
                            CASE 
                                WHEN is_nullable = 'NO' THEN ' NOT NULL'
                                ELSE ''
                            END,
                            ', '
                        ) || ');' as ddl
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    GROUP BY table_name
                """
                
                result = conn.execute(text(ddl_query))
                ddl = result.fetchone()[0]
                
                # Train Vanna with DDL
                self.vn.add_ddl(ddl)
                print(f"   ✓ Added DDL for {table_name}")
        
    def _train_firebase_schema(self):
        """Train on Firebase collections schema"""
        print("\n2. Training on Firebase Collections...")
        
        # Get all collections
        collections = self.firebase_db.collections()
        
        for collection in collections:
            collection_name = collection.id
            
            # Get sample documents to infer schema
            docs = collection.limit(10).stream()
            
            # Collect all unique fields
            fields = set()
            sample_data = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                fields.update(doc_data.keys())
                sample_data.append(doc_data)
            
            if fields:
                # Create a pseudo-DDL for Firebase collection
                firebase_ddl = f"""
                -- FIREBASE COLLECTION: {collection_name}
                -- This is a NoSQL collection in Firebase, not a SQL table
                -- Access via: FIREBASE_QUERY: {collection_name}
                CREATE TABLE firebase_{collection_name} (
                    id TEXT PRIMARY KEY,
                    {', '.join([f"{field} TEXT" for field in sorted(fields)])}
                );
                -- Sample document count: {len(sample_data)}
                """
                
                # Add as documentation
                self.vn.add_documentation(firebase_ddl)
                print(f"   ✓ Added Firebase collection: {collection_name} ({len(fields)} fields)")
    
    def _train_routing_logic(self):
        """Train on how to route queries between databases"""
        print("\n3. Training routing logic...")
        
        routing_doc = """
        ROUTING RULES FOR QUERIES:
        
        1. NEON PostgreSQL Database contains:
           - projects (project management)
           - sow_drops (customer connections) 
           - sow_poles (infrastructure)
           - sow_fibre (cable segments)
           - nokia_data (equipment)
           - status_changes (history)
           - All other SQL tables
        
        2. Firebase Firestore contains:
           - staff (employee/personnel data)
           - users (system users)
           - real-time updates
           - Any collection-based data
        
        3. Query Routing:
           - Questions about staff/employees/personnel → FIREBASE_QUERY: staff
           - Questions about users/accounts → FIREBASE_QUERY: users  
           - Questions about drops/poles/projects → SQL query
           - Questions about equipment/nokia → SQL query
           - Default → SQL query
        
        4. Special syntax:
           - For Firebase: Return "FIREBASE_QUERY: collection_name"
           - For SQL: Return standard PostgreSQL query
        """
        
        self.vn.add_documentation(routing_doc)
        print("   ✓ Added routing documentation")
    
    def _train_example_queries(self):
        """Train on example queries for both databases"""
        print("\n4. Training on example queries...")
        
        examples = [
            # SQL Examples (Neon)
            {
                "question": "How many drops are in the system?",
                "sql": "SELECT COUNT(*) FROM sow_drops;"
            },
            {
                "question": "Show all projects",
                "sql": "SELECT * FROM projects ORDER BY created_at DESC;"
            },
            {
                "question": "List poles in Lawley",
                "sql": """SELECT * FROM sow_poles 
                         WHERE pole_number LIKE 'LAW%' 
                         LIMIT 100;"""
            },
            
            # Firebase Examples
            {
                "question": "List all staff",
                "sql": "FIREBASE_QUERY: staff"
            },
            {
                "question": "Show all employees",
                "sql": "FIREBASE_QUERY: staff"
            },
            {
                "question": "Who are the field agents?",
                "sql": "FIREBASE_QUERY: staff WHERE role='field_agent'"
            },
            {
                "question": "List system users",
                "sql": "FIREBASE_QUERY: users"
            },
            
            # Mixed/Complex Examples
            {
                "question": "Which staff member installed the most drops?",
                "sql": """-- First query SQL for installations
                         SELECT installed_by, COUNT(*) as count 
                         FROM project_drops 
                         WHERE installed_by IS NOT NULL 
                         GROUP BY installed_by
                         ORDER BY count DESC;
                         -- Then match with FIREBASE_QUERY: staff"""
            }
        ]
        
        for example in examples:
            self.vn.add_question_sql(
                question=example["question"],
                sql=example["sql"]
            )
            print(f"   ✓ Added: {example['question'][:50]}...")
        
        print(f"   Total examples added: {len(examples)}")
    
    def _verify_training(self):
        """Verify the training worked"""
        print("\n5. Verifying training...")
        
        # Get training data
        training_data = self.vn.get_training_data()
        
        if hasattr(training_data, '__len__'):
            print(f"   ✓ Total training items: {len(training_data)}")
        
        # Test a few queries
        test_queries = [
            "How many drops are there?",
            "List all staff",
            "Show projects"
        ]
        
        print("\n   Testing query generation:")
        for q in test_queries:
            try:
                # This would normally use vn.generate_sql() but we need
                # to implement the generate_sql method for our custom class
                print(f"   Q: {q}")
                # For now, just show it's trained
                related = self.vn.get_related_training_data(q)
                if related:
                    print(f"   ✓ Found {len(related)} related training examples")
            except Exception as e:
                print(f"   ! Error: {e}")

if __name__ == "__main__":
    trainer = VannaTrainer()
    trainer.train_complete_system()