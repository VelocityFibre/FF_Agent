#!/usr/bin/env python3
"""
Simple test to verify the enhanced prompt system is working
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_query(question: str, use_vector: bool = False):
    """Test a single query"""
    print(f"\n{'='*60}")
    print(f"Query: {question}")
    print(f"Vector Search: {'Yes' if use_vector else 'No'}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={
                "question": question,
                "use_vector_search": use_vector
            },
            timeout=30
        )
        result = response.json()
        
        # Show classification
        if result.get('query_classification'):
            cls = result['query_classification']
            print(f"\n✅ Classification Detected:")
            print(f"   Type: {cls.get('type')}")
            print(f"   Databases: {cls.get('databases')}")
            print(f"   Complexity: {cls.get('complexity')}")
        
        # Show entities
        if result.get('entities_detected'):
            print(f"\n✅ Entities Detected:")
            for category, items in result['entities_detected'].items():
                print(f"   {category}: {items}")
        
        # Show SQL
        if result.get('sql'):
            print(f"\n📝 Generated SQL:")
            print(f"   {result['sql'][:200]}...")
        
        # Show success/error
        if result.get('success'):
            print(f"\n✅ Query Successful!")
            print(f"   Rows returned: {result.get('row_count', 0)}")
        else:
            print(f"\n❌ Error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

# Test queries
print("🚀 TESTING ENHANCED PROMPT SYSTEM (WITHOUT VECTOR SEARCH)")
print("="*60)

# Test 1: Firebase routing
test_query("List all staff", use_vector=False)

# Test 2: PostgreSQL with project code
test_query("Show drops in Lawley", use_vector=False)

# Test 3: Telecom term detection
test_query("What's the PON utilization?", use_vector=False)

# Test 4: Hybrid query
test_query("Which technician installed the most drops?", use_vector=False)

print("\n✅ Test complete!")