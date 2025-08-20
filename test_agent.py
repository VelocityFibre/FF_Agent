#!/usr/bin/env python3
from ff_agent_gemini import FF_Agent_Gemini
import json

def test_queries():
    print("Testing FF_Agent with Real Queries")
    print("=" * 60)
    
    agent = FF_Agent_Gemini()
    
    test_queries = [
        "How many total drops are in the system?",
        "Show me all projects and their creation dates",
        "What's the breakdown of status changes by type?",
        "How many poles are in the Lawley project?",
        "Show me the top 5 poles with the most drops connected"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        print("-" * 50)
        
        try:
            result = agent.query_with_context(query)
            
            if result["success"]:
                print(f"✅ Success!")
                print(f"Answer: {result['data']}")
            else:
                print(f"❌ Error: {result['error']}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_queries()