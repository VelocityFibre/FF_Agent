#!/usr/bin/env python3
"""
Quick test of various Firebase queries
"""

import requests
import json

API_URL = "http://localhost:8000/query"

test_queries = [
    # Meeting queries - testing singular vs plural
    "what was the most recent meeting",
    "show me the last 5 meetings", 
    "latest meeting insights",
    "meetings with action items",
    
    # Staff queries
    "show me all staff",
    "who are the employees",
    
    # Task queries
    "show me open tasks",
    "latest tasks",
    
    # Field operations
    "recent field pole installations",
    
    # SQL queries (should still work)
    "how many drops in LAW001",
    "total poles in the system"
]

def test_query(question):
    """Test a single query and show results"""
    print(f"\n{'='*60}")
    print(f"Query: {question}")
    print('-'*60)
    
    try:
        response = requests.post(API_URL, json={"question": question})
        result = response.json()
        
        if result['success']:
            print(f"✓ Success - {result['row_count']} rows returned")
            print(f"Type: {result['sql'][:50]}...")
            
            # Show first result if available
            if result['data'] and isinstance(result['data'], list) and len(result['data']) > 0:
                first = result['data'][0]
                if isinstance(first, dict):
                    print("\nFirst result:")
                    # Show up to 5 fields
                    for i, (key, value) in enumerate(list(first.items())[:5]):
                        print(f"  {key}: {str(value)[:80]}")
                    if len(first) > 5:
                        print(f"  ... and {len(first) - 5} more fields")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("Testing Query Improvements")
    print("="*60)
    
    for query in test_queries:
        test_query(query)
    
    print("\n" + "="*60)
    print("Done!")