#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("NEON_DATABASE_URL")
engine = create_engine(database_url)

with engine.connect() as conn:
    # Get all tables
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    
    tables = result.fetchall()
    print(f"Found {len(tables)} tables in Neon database:\n")
    
    for table in tables:
        table_name = table[0]
        # Get row count
        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = count_result.fetchone()[0]
        
        # Get columns
        col_result = conn.execute(text(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """))
        columns = col_result.fetchall()
        
        print(f"📊 {table_name}: {count} rows")
        for col_name, col_type in columns[:5]:  # Show first 5 columns
            print(f"   - {col_name} ({col_type})")
        if len(columns) > 5:
            print(f"   ... and {len(columns) - 5} more columns")
        print()