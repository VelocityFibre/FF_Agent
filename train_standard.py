#!/usr/bin/env python3
"""
Train Vanna using STANDARD methods from Vanna documentation
This uses Vanna's cloud service for simplicity
"""

import os
from dotenv import load_dotenv
import vanna
from vanna.remote import VannaDefault
from sqlalchemy import create_engine, text
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Get Vanna API key (free at vanna.ai)
# For demo, using email-based key
api_key = vanna.get_api_key(email='louis@velocityfibre.com')

# Initialize Vanna with standard method
vn = VannaDefault(model='fibreflow-model', api_key=api_key)

# Connect to your database
vn.connect_to_postgres(
    host='ep-long-breeze-a9w7xool.gwc.azure.neon.tech',
    dbname='neondb',
    user='neondb_owner',
    password='npg_AlX83ojfZpBk',
    port=5432
)

print("="*60)
print("TRAINING VANNA USING STANDARD METHODS")
print("="*60)

# 1. Train on DDL (Database Schema)
print("\n1. Training on DDL from information schema...")
# Vanna can auto-extract DDL
ddl_query = """
    SELECT 
        'CREATE TABLE ' || table_name || ' (' ||
        string_agg(
            column_name || ' ' || data_type,
            ', '
        ) || ');' as ddl
    FROM information_schema.columns
    WHERE table_schema = 'public'
    GROUP BY table_name
    LIMIT 10
"""

df_ddl = vn.run_sql(ddl_query)
for ddl in df_ddl['ddl'].values:
    vn.train(ddl=ddl)
    print(f"   ✓ Trained on: {ddl[:50]}...")

# 2. Train on Documentation
print("\n2. Training on documentation...")
doc = """
FibreFlow Database System:

SQL Database (Neon PostgreSQL):
- projects: Project management (5 projects)
- sow_drops: Customer connections (23,707 drops)
- sow_poles: Infrastructure poles (4,471 poles)
- sow_fibre: Fiber segments
- nokia_data: Equipment records (327 units)
- status_changes: History tracking

Firebase Collections (NoSQL):
- staff: Employee records (name, role, department)
- users: System users
- Real-time status updates

IMPORTANT ROUTING:
- Questions about staff/employees → Return "FIREBASE_QUERY: staff"
- Questions about drops/poles/projects → Normal SQL
"""

vn.train(documentation=doc)
print("   ✓ Added system documentation")

# 3. Train on Question-SQL pairs
print("\n3. Training on example queries...")

training_pairs = [
    # SQL queries
    ("How many drops are in the system?", 
     "SELECT COUNT(*) as total_drops FROM sow_drops;"),
    
    ("Show all projects",
     "SELECT project_code, name, created_at FROM projects ORDER BY created_at DESC;"),
    
    ("How many poles are there?",
     "SELECT COUNT(DISTINCT pole_number) FROM sow_poles;"),
    
    ("List drops in Lawley",
     "SELECT * FROM sow_drops WHERE pole_number LIKE 'LAW%' LIMIT 100;"),
    
    # Firebase queries
    ("List all staff",
     "FIREBASE_QUERY: staff"),
    
    ("Show all employees", 
     "FIREBASE_QUERY: staff"),
    
    ("Who are the field agents?",
     "FIREBASE_QUERY: staff WHERE role='field_agent'"),
    
    ("Show system users",
     "FIREBASE_QUERY: users"),
]

for question, sql in training_pairs:
    vn.train(question=question, sql=sql)
    print(f"   ✓ {question}")

print(f"\nTotal examples trained: {len(training_pairs)}")

# 4. Test the training
print("\n4. Testing trained model...")
test_questions = [
    "How many drops are there?",
    "List all staff",
    "Show me the projects"
]

for q in test_questions:
    print(f"\nQ: {q}")
    try:
        sql = vn.generate_sql(q)
        print(f"A: {sql}")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*60)
print("✅ Training complete! Vanna is ready to use.")
print("="*60)