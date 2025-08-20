#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

def run_direct_queries():
    print("=" * 60)
    print("DIRECT SQL TEST - FIBREFLOW DATA")
    print("=" * 60)
    
    database_url = os.getenv("NEON_DATABASE_URL")
    engine = create_engine(database_url)
    
    queries = {
        "1. Drops in Lawley project": """
            SELECT COUNT(*) as drop_count 
            FROM sow_drops 
            WHERE drop_number LIKE 'LAW%' OR pole_number LIKE 'LAW%'
        """,
        
        "2. Total poles in system": """
            SELECT COUNT(DISTINCT pole_number) as total_poles 
            FROM sow_poles
        """,
        
        "3. Pole status breakdown": """
            SELECT status, COUNT(*) as count 
            FROM sow_poles 
            GROUP BY status 
            ORDER BY count DESC
        """,
        
        "4. Projects with drop counts": """
            SELECT p.name, p.project_code,
                   COUNT(DISTINCT sd.drop_number) as drops
            FROM projects p
            LEFT JOIN sow_drops sd ON sd.project_id = p.firebase_id
            GROUP BY p.name, p.project_code
            ORDER BY drops DESC
        """,
        
        "5. Top 5 poles by drops": """
            SELECT pole_number, COUNT(*) as drop_count
            FROM sow_drops
            WHERE pole_number IS NOT NULL
            GROUP BY pole_number
            ORDER BY drop_count DESC
            LIMIT 5
        """
    }
    
    with engine.connect() as conn:
        for title, query in queries.items():
            print(f"\n📊 {title}")
            print("-" * 40)
            try:
                result = pd.read_sql_query(query, conn)
                if result.empty:
                    print("No data found")
                else:
                    print(result.to_string(index=False))
            except Exception as e:
                print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Direct SQL tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    run_direct_queries()