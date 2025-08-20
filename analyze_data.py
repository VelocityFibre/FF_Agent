#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

database_url = os.getenv("NEON_DATABASE_URL")
engine = create_engine(database_url)

with engine.connect() as conn:
    print("=" * 60)
    print("FIBREFLOW DATA ANALYSIS")
    print("=" * 60)
    
    # 1. Projects Overview
    print("\n📋 PROJECTS:")
    result = conn.execute(text("""
        SELECT project_code, name, 
               created_at::date as created,
               firebase_id
        FROM projects
        ORDER BY created_at DESC
    """))
    for row in result:
        print(f"  • {row[0]}: {row[1]} (Created: {row[2]})")
    
    # 2. Poles by Project
    print("\n📍 POLES BY PROJECT:")
    result = conn.execute(text("""
        SELECT p.project_code, 
               COUNT(DISTINCT sp.pole_number) as pole_count,
               COUNT(DISTINCT CASE WHEN sp.status = 'Complete' THEN sp.pole_number END) as completed
        FROM sow_poles sp
        JOIN projects p ON sp.project_id = p.project_code
        GROUP BY p.project_code
        ORDER BY pole_count DESC
    """))
    for row in result:
        print(f"  • {row[0]}: {row[1]} poles ({row[2]} completed)")
    
    # 3. Drops Summary
    print("\n🏠 DROPS SUMMARY:")
    result = conn.execute(text("""
        SELECT COUNT(*) as total_drops,
               COUNT(DISTINCT pole_number) as unique_poles,
               COUNT(DISTINCT project_id) as projects
        FROM sow_drops
    """))
    row = result.fetchone()
    print(f"  • Total Drops: {row[0]:,}")
    print(f"  • Connected to: {row[1]:,} poles")
    print(f"  • Across: {row[2]} projects")
    
    # 4. Status Changes Summary
    print("\n🔄 STATUS CHANGES SUMMARY:")
    result = conn.execute(text("""
        SELECT status, COUNT(*) as count
        FROM status_changes
        GROUP BY status
        ORDER BY count DESC
        LIMIT 5
    """))
    for row in result:
        print(f"  • {row[0]}: {row[1]} changes")
    
    # 5. Nokia Equipment
    print("\n📡 NOKIA EQUIPMENT STATUS:")
    result = conn.execute(text("""
        SELECT status, COUNT(*) as count
        FROM nokia_data
        WHERE status IS NOT NULL
        GROUP BY status
        ORDER BY count DESC
    """))
    for row in result:
        print(f"  • {row[0]}: {row[1]} units")
    
    # 6. Firebase Sync Status
    print("\n🔄 FIREBASE SYNC:")
    result = conn.execute(text("""
        SELECT collection, 
               COUNT(*) as doc_count,
               MAX(last_updated)::date as last_sync
        FROM firebase_current_state
        GROUP BY collection
        ORDER BY doc_count DESC
    """))
    for row in result:
        print(f"  • {row[0]}: {row[1]} docs (Last: {row[2]})")
    
    print("\n" + "=" * 60)