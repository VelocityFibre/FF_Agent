"""
Re-seed embeddings with ada-002 model for better similarity scores
"""

from vector_store import VectorStore
import os
from dotenv import load_dotenv

load_dotenv()

def reseed_embeddings():
    """Clear old embeddings and re-seed with ada-002"""
    print("🔄 Re-seeding embeddings with ada-002 model...")
    
    vector_store = VectorStore()
    
    # Clear existing embeddings
    with vector_store.get_connection() as conn:
        with conn.cursor() as cur:
            print("🗑️  Clearing old embeddings...")
            cur.execute("TRUNCATE TABLE query_embeddings, schema_embeddings, error_patterns RESTART IDENTITY")
            conn.commit()
            print("✅ Old embeddings cleared")
    
    # Re-index schema with ada-002
    schema_definitions = [
        # FibreFlow schema
        {"table_name": "customers", "column_name": "customer_id", "description": "Unique customer identifier"},
        {"table_name": "customers", "column_name": "customer_name", "description": "Customer business name"},
        {"table_name": "customers", "column_name": "email", "description": "Customer email address"},
        {"table_name": "customers", "column_name": "last_order_date", "description": "Date of customer's most recent order"},
        {"table_name": "customers", "column_name": "status", "description": "Customer account status (active, inactive, suspended)"},
        
        {"table_name": "orders", "column_name": "order_id", "description": "Unique order identifier"},
        {"table_name": "orders", "column_name": "customer_id", "description": "Reference to customer who placed order"},
        {"table_name": "orders", "column_name": "order_date", "description": "Date when order was placed"},
        {"table_name": "orders", "column_name": "total_amount", "description": "Total order value in currency"},
        {"table_name": "orders", "column_name": "status", "description": "Order status (pending, shipped, delivered, cancelled)"},
        
        {"table_name": "products", "column_name": "product_id", "description": "Unique product identifier"},
        {"table_name": "products", "column_name": "product_name", "description": "Name of the product"},
        {"table_name": "products", "column_name": "category", "description": "Product category classification"},
        {"table_name": "products", "column_name": "price", "description": "Product unit price"},
        {"table_name": "products", "column_name": "stock_quantity", "description": "Current inventory level"},
        
        {"table_name": "order_items", "column_name": "order_id", "description": "Reference to order"},
        {"table_name": "order_items", "column_name": "product_id", "description": "Reference to product"},
        {"table_name": "order_items", "column_name": "quantity", "description": "Number of units ordered"},
        {"table_name": "order_items", "column_name": "unit_price", "description": "Price per unit at time of order"},
    ]
    
    print("📊 Re-indexing schema with ada-002...")
    vector_store.index_schema(schema_definitions)
    
    # Re-seed example queries with ada-002
    example_queries = [
        {
            "question": "Show all active customers",
            "sql": "SELECT * FROM customers WHERE status = 'active'",
            "execution_time": 0.045
        },
        {
            "question": "Display customers with active status",
            "sql": "SELECT * FROM customers WHERE status = 'active'",
            "execution_time": 0.043
        },
        {
            "question": "Get total sales for last month",
            "sql": """SELECT SUM(total_amount) as total_sales 
                     FROM orders 
                     WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                     AND order_date < DATE_TRUNC('month', CURRENT_DATE)""",
            "execution_time": 0.082
        },
        {
            "question": "Find customers who haven't ordered in 30 days",
            "sql": """SELECT c.* FROM customers c 
                     WHERE c.last_order_date < CURRENT_DATE - INTERVAL '30 days'
                     OR c.last_order_date IS NULL""",
            "execution_time": 0.067
        },
        {
            "question": "Show top 10 products by sales",
            "sql": """SELECT p.product_name, SUM(oi.quantity * oi.unit_price) as total_sales
                     FROM products p
                     JOIN order_items oi ON p.product_id = oi.product_id
                     GROUP BY p.product_id, p.product_name
                     ORDER BY total_sales DESC
                     LIMIT 10""",
            "execution_time": 0.125
        },
        {
            "question": "List customers that are active",
            "sql": "SELECT * FROM customers WHERE status = 'active'",
            "execution_time": 0.041
        },
        {
            "question": "Which customers are currently active",
            "sql": "SELECT customer_id, customer_name, email FROM customers WHERE status = 'active'",
            "execution_time": 0.039
        }
    ]
    
    print("🌱 Re-seeding example queries with ada-002...")
    for example in example_queries:
        vector_store.store_successful_query(
            question=example["question"],
            sql_query=example["sql"],
            execution_time=example["execution_time"]
        )
    
    print("✅ Re-seeding complete with ada-002 embeddings!")
    
    # Test the improved similarity
    print("\n📊 Testing improved similarity scores:")
    print("-" * 50)
    
    test_queries = [
        "Show active customers",
        "Display customers with active status",
        "List all active customers"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = vector_store.find_similar_queries(query, limit=3)
        if results:
            for r in results[:2]:
                print(f"  → {r['question'][:40]}... (similarity: {r['similarity']:.1%})")
        else:
            print("  → No similar queries found")

if __name__ == "__main__":
    reseed_embeddings()