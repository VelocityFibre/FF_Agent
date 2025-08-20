#!/usr/bin/env python3
from ff_agent_gemini import FF_Agent_Gemini
import json
import time

def run_test_queries():
    print("=" * 60)
    print("FF_AGENT TEST SUITE - FIBREFLOW DATA")
    print("=" * 60)
    
    try:
        print("\n⏳ Initializing FF_Agent...")
        agent = FF_Agent_Gemini()
        print("✅ Agent initialized successfully!\n")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    test_queries = [
        "How many drops are in the Lawley project?",
        "Show me the total number of poles in the system",
        "What are the different pole statuses and their counts?",
        "List all projects with their drop counts",
        "Show me the top 5 poles with the most drops connected"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {query}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            result = agent.query(query)
            elapsed = time.time() - start_time
            
            if result["success"]:
                print(f"✅ SUCCESS (took {elapsed:.2f}s)")
                print(f"\nRESPONSE:")
                # Limit output for readability
                response_str = str(result['data'])
                if len(response_str) > 500:
                    print(response_str[:500] + "...")
                else:
                    print(response_str)
                
                results.append({
                    "query": query,
                    "status": "SUCCESS",
                    "time": elapsed
                })
            else:
                print(f"❌ FAILED: {result['error']}")
                results.append({
                    "query": query,
                    "status": "FAILED",
                    "error": result['error']
                })
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
            results.append({
                "query": query,
                "status": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    total_count = len(results)
    
    print(f"\n✅ Passed: {success_count}/{total_count}")
    print(f"❌ Failed: {total_count - success_count}/{total_count}")
    
    if success_count > 0:
        avg_time = sum(r.get("time", 0) for r in results if r["status"] == "SUCCESS") / success_count
        print(f"⚡ Avg response time: {avg_time:.2f}s")
    
    print("\nDetailed Results:")
    for i, r in enumerate(results, 1):
        status_emoji = "✅" if r["status"] == "SUCCESS" else "❌"
        print(f"{status_emoji} Test {i}: {r['status']}")
        if r["status"] != "SUCCESS" and "error" in r:
            print(f"   Error: {r['error'][:100]}...")

if __name__ == "__main__":
    run_test_queries()