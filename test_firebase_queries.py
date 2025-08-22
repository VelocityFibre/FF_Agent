#!/usr/bin/env python3
"""
Test script for Firebase query improvements
"""

import requests
import json
from datetime import datetime

# API endpoint
API_URL = "http://localhost:8000/query"

def test_query(question: str, description: str):
    """Test a single query"""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Question: {question}")
    print('-'*60)
    
    try:
        response = requests.post(API_URL, json={"question": question})
        result = response.json()
        
        if result['success']:
            print(f"✓ Success - {result['row_count']} rows returned")
            print(f"SQL/Firebase: {result['sql']}")
            
            # Show sample data
            if result['data'] and isinstance(result['data'], list):
                print(f"\nSample data (first 2 records):")
                for i, record in enumerate(result['data'][:2]):
                    print(f"\n  Record {i+1}:")
                    if isinstance(record, dict):
                        # Show key fields
                        for key in ['title', 'dateTime', 'key_insights', 'organizer', 'status']:
                            if key in record:
                                value = str(record[key])[:100]  # Truncate long values
                                print(f"    {key}: {value}")
            else:
                print(f"Data: {result['data']}")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Error making request: {e}")

def main():
    """Run all tests"""
    print("Testing Firebase Query Improvements")
    print("="*60)
    
    # Test cases for meetings
    test_cases = [
        ("latest meetings insights", "Get latest meeting insights"),
        ("show me recent meetings", "Get recent meetings"),
        ("meetings with action items", "Get meetings with action items"),
        ("today's meetings", "Get today's meetings"),
        ("meetings this week", "Get this week's meetings"),
        ("meeting insights from last 10 meetings", "Get insights from recent meetings"),
        
        # Test cases for tasks
        ("show me open tasks", "Get open tasks"),
        ("latest tasks created", "Get recently created tasks"),
        ("overdue tasks", "Get overdue tasks"),
        
        # Test cases for field operations
        ("latest field pole installations", "Get recent field installations"),
        ("pole plantings in Lawley", "Get Lawley pole plantings"),
    ]
    
    for question, description in test_cases:
        test_query(question, description)
    
    print("\n" + "="*60)
    print("Testing complete!")

if __name__ == "__main__":
    main()