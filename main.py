#!/usr/bin/env python3
from ff_agent_gemini import FF_Agent_Gemini
import json


def main():
    """Main interface for FF_Agent"""
    
    print("=" * 50)
    print("FF_Agent - AI Database Query Assistant")
    print("=" * 50)
    print("\nInitializing FF_Agent...")
    
    try:
        agent = FF_Agent_Gemini()
        print("✓ FF_Agent ready!")
        print("\nCommands:")
        print("  - Type your question to query data")
        print("  - Type 'quit' to exit\n")
        
        while True:
            question = input("\n[FF_Agent] > ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\nFF_Agent shutting down. Goodbye!")
                break
            
            if not question:
                continue
            
            print("\n⏳ Processing...")
            
            try:
                result = agent.query_with_context(question)
                
                if result["success"]:
                    print(f"\n✓ Source: {result['source']}")
                    print(f"Result:\n{json.dumps(result['data'], indent=2)}")
                else:
                    print(f"\n✗ Error: {result['error']}")
                    
            except Exception as e:
                print(f"\n✗ Unexpected error: {e}")
                
    except Exception as e:
        print(f"\n✗ Failed to initialize FF_Agent: {e}")
        print("\nPlease check your .env configuration:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your API keys and database credentials")
        print("  3. Ensure firebase-credentials.json exists")


def example_usage():
    """Example usage patterns for FF_Agent"""
    agent = FF_Agent_Gemini()
    
    print("\n" + "=" * 50)
    print("FF_Agent Example Queries")
    print("=" * 50)
    
    example_queries = [
        ("Show me all users who signed up in the last 30 days", "neon"),
        ("What is the total revenue this month?", "neon"),
        ("Get all active subscriptions from Firebase", "firebase"),
        ("Show me the top 10 customers by order value", "neon"),
        ("How many products are in stock?", "neon"),
        ("List all orders with status 'pending'", "auto")
    ]
    
    for query, source in example_queries:
        print(f"\n📊 Query: {query}")
        print(f"   Source: {source}")
        result = agent.query(query, source=source)
        if result["success"]:
            print(f"   ✓ Result preview: {str(result['data'])[:100]}...")
        else:
            print(f"   ✗ Error: {result['error']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "examples":
        example_usage()
    else:
        main()