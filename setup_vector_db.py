"""
Setup script for initializing pgvector in Neon database
Run this once to set up the vector database tables and indexes
"""

from vector_store import VectorStore
import os
from dotenv import load_dotenv

load_dotenv()

def setup_vector_database():
    """Initialize pgvector and create necessary tables"""
    print("🚀 Setting up vector database...")
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Create tables and extensions
    vector_store.initialize_pgvector()
    
    # Index your existing schema
    # Add your schema definitions here
    sample_schema = [
        # FibreFlow schema examples - update with your actual schema
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
        
        # Firebase collections
        {"table_name": "firebase_users", "column_name": "uid", "description": "Firebase user unique identifier"},
        {"table_name": "firebase_users", "column_name": "email", "description": "User email address"},
        {"table_name": "firebase_users", "column_name": "created_at", "description": "Account creation timestamp"},
        
        {"table_name": "firebase_sessions", "column_name": "session_id", "description": "Session identifier"},
        {"table_name": "firebase_sessions", "column_name": "user_id", "description": "User who owns the session"},
        {"table_name": "firebase_sessions", "column_name": "start_time", "description": "Session start timestamp"},
    ]
    
    print("📊 Indexing schema definitions...")
    vector_store.index_schema(sample_schema)
    
    # Seed with some example successful queries (optional)
    seed_examples = [
        {
            "question": "Show all active customers",
            "sql": "SELECT * FROM customers WHERE status = 'active'",
            "execution_time": 0.045
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
        }
    ]
    
    print("🌱 Seeding example queries...")
    for example in seed_examples:
        vector_store.store_successful_query(
            question=example["question"],
            sql_query=example["sql"],
            execution_time=example["execution_time"]
        )
    
    print("✅ Vector database setup complete!")
    print("\nNext steps:")
    print("1. Update your schema definitions in this file with your actual tables")
    print("2. Run: python setup_vector_db.py")
    print("3. Your agent will now have semantic search capabilities!")

if __name__ == "__main__":
    setup_vector_database()