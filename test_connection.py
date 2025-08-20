#!/usr/bin/env python3
"""Test script to verify database connections"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json

load_dotenv()

def test_neon_connection():
    """Test Neon database connection"""
    print("\n" + "="*50)
    print("Testing Neon Database Connection")
    print("="*50)
    
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        print("❌ NEON_DATABASE_URL not found in .env")
        return False
    
    print(f"Connecting to: {database_url.split('@')[1].split('/')[0]}...")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {version}")
            
            # Get table list
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"\n📊 Found {len(tables)} tables:")
                for table in tables[:10]:  # Show first 10 tables
                    # Get row count
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.fetchone()[0]
                    print(f"   - {table}: {count} rows")
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more tables")
            else:
                print("\n⚠️  No tables found in database")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_gemini_connection():
    """Test Gemini API connection"""
    print("\n" + "="*50)
    print("Testing Gemini API Connection")
    print("="*50)
    
    api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    if not api_key:
        print("❌ GOOGLE_AI_STUDIO_API_KEY not found in .env")
        return False
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            temperature=0.1,
            google_api_key=api_key
        )
        
        # Test with simple prompt
        response = llm.invoke("Say 'Connection successful' if you can read this")
        print(f"✅ Gemini API connected!")
        print(f"   Model: {os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')}")
        print(f"   Response: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        return False

def test_firebase_connection():
    """Test Firebase connection"""
    print("\n" + "="*50)
    print("Testing Firebase Connection")
    print("="*50)
    
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
    
    if not os.path.exists(cred_path):
        print(f"⚠️  Firebase credentials not found at: {cred_path}")
        print("   Firebase queries will be disabled")
        return False
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        
        # Try to list collections
        collections = db.collections()
        collection_names = [c.id for c in collections]
        
        print(f"✅ Firebase connected!")
        print(f"   Project: {os.getenv('FIREBASE_PROJECT_ID', 'unknown')}")
        if collection_names:
            print(f"   Collections found: {', '.join(collection_names[:5])}")
        else:
            print("   No collections found (empty database)")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Firebase connection failed: {e}")
        print("   Firebase queries will be disabled")
        return False

def main():
    print("\n🚀 FF_Agent Connection Test Suite")
    
    results = {
        "Neon": test_neon_connection(),
        "Gemini": test_gemini_connection(),
        "Firebase": test_firebase_connection()
    }
    
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    
    for service, status in results.items():
        emoji = "✅" if status else "❌"
        print(f"{emoji} {service}: {'Connected' if status else 'Failed'}")
    
    if all(results.values()):
        print("\n🎉 All connections successful! FF_Agent is ready to use.")
    elif results["Neon"] and results["Gemini"]:
        print("\n✅ Core services connected. FF_Agent can run with limited features.")
    else:
        print("\n⚠️  Some connections failed. Please check your configuration.")
    
    return 0 if (results["Neon"] and results["Gemini"]) else 1

if __name__ == "__main__":
    sys.exit(main())