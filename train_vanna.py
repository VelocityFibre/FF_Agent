#!/usr/bin/env python3
"""
Train Vanna with your database schema and Firebase collections
Uses Vanna's built-in training methods
"""

from ff_agent_vanna import FF_Agent_Vanna
import json

def train_agent():
    print("Training Vanna with database knowledge...")
    
    agent = FF_Agent_Vanna()
    
    # 1. Train on Information Schema (automatic schema discovery)
    print("\n1. Training on database schema...")
    # Vanna automatically discovers tables when connected
    
    # 2. Add Firebase documentation
    print("\n2. Adding Firebase collections documentation...")
    agent.vn.train(documentation="""
    FIREBASE COLLECTIONS (Firestore):
    
    staff collection: Contains all staff/employee records
    - Fields: name, email, role, department, phone, employee_id
    - Used for: Employee management, authentication, assignments
    
    users collection: System users and customers
    - Fields: uid, email, displayName, role, createdAt
    
    projects collection: Mirrors projects table but with real-time updates
    - Fields: Same as Neon projects table
    
    status_changes collection: Real-time status updates
    - Synced with Neon status_changes table
    
    IMPORTANT: When asked about staff, employees, or personnel:
    - This data is ONLY in Firebase 'staff' collection
    - Use Firebase queries, not SQL
    """)
    
    # 3. Train on cross-database queries
    print("\n3. Training on cross-database query patterns...")
    training_examples = [
        # Staff queries (Firebase)
        ("List all staff", 
         "This requires Firebase query on 'staff' collection"),
        
        ("Show me all employees",
         "This requires Firebase query on 'staff' collection"),
        
        ("Who are the field agents?",
         "Query Firebase 'staff' collection where role = 'field_agent'"),
        
        # Mixed queries
        ("Which staff member installed the most drops?",
         """First get installations from SQL:
         SELECT installed_by, COUNT(*) as count 
         FROM project_drops 
         WHERE installed_by IS NOT NULL 
         GROUP BY installed_by
         Then match with Firebase staff collection"""),
         
        # Clear SQL queries
        ("How many drops in Lawley?",
         "SELECT COUNT(*) FROM sow_drops WHERE project_id = (SELECT firebase_id FROM projects WHERE name = 'Lawley')"),
    ]
    
    for question, answer in training_examples:
        agent.vn.train(question=question, sql=answer)
    
    # 4. Show what Vanna has learned
    print("\n4. Current training data:")
    training_data = agent.vn.get_training_data()
    
    if hasattr(training_data, 'shape'):
        print(f"   Total training items: {len(training_data)}")
    else:
        print(f"   Training data: {training_data}")
    
    print("\n✅ Training complete!")
    
    # 5. Test the training
    print("\n5. Testing trained knowledge:")
    test_questions = [
        "List all staff",
        "How many projects are there?",
        "Show drops in Lawley"
    ]
    
    for q in test_questions:
        print(f"\n   Q: {q}")
        try:
            result = agent.vn.generate_sql(q)
            print(f"   A: {result[:100]}...")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    train_agent()