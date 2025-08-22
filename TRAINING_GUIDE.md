# How to Train FF_Agent to Know Which Database to Use

## The Problem
- **Neon PostgreSQL** has: projects, drops, poles, equipment
- **Firebase** has: staff, users, real-time data
- The agent needs to know which database to query

## Solution: Training the Agent

### Method 1: Simple Prompt Engineering (Currently Used)
```python
# In api.py, we tell Gemini:
"IMPORTANT: Staff/employee data is ONLY in Firebase.
If asked about staff, return: FIREBASE_QUERY: staff"
```

### Method 2: Vanna AI Training (Professional Solution)

Vanna learns from 3 types of training:

1. **DDL (Database Schema)**
```python
vn.train(ddl="CREATE TABLE sow_drops (drop_number TEXT, ...)")
```

2. **Documentation**
```python
vn.train(documentation="""
Firebase has:
- staff collection: All employee data
- users collection: System users
""")
```

3. **Question-SQL Pairs**
```python
vn.train(
    question="List all staff",
    sql="FIREBASE_QUERY: staff"
)
```

## How It Works

When you ask: **"List all staff"**

1. **Without Training:**
   - Agent tries SQL: `SELECT * FROM staff` ❌ (no staff table in SQL)

2. **With Training:**
   - Agent knows: staff = Firebase
   - Returns: `FIREBASE_QUERY: staff` ✅
   - API routes to Firebase

## Current Implementation

The API checks the SQL response:
```python
if "FIREBASE_QUERY:" in sql:
    # Query Firebase
    collection = extract_collection(sql)
    data = firebase.collection(collection).get()
else:
    # Query PostgreSQL
    data = execute_sql(sql)
```

## To Add More Training

Edit `api.py` and add to the prompt:
```python
"""
Firebase collections:
- staff: employees (name, role, department)
- users: system users
- inventory: stock levels
- alerts: real-time notifications

SQL tables:
- projects, sow_drops, sow_poles: infrastructure
- nokia_data: equipment
"""
```

## Manual Training Commands

```python
# Train that "personnel" also means staff
vn.train(
    question="Show all personnel",
    sql="FIREBASE_QUERY: staff"
)

# Train complex queries
vn.train(
    question="Which employee installed the most drops?",
    sql="""
    -- Get installations from SQL
    SELECT installed_by, COUNT(*) FROM project_drops
    GROUP BY installed_by ORDER BY COUNT(*) DESC;
    -- Then match with FIREBASE_QUERY: staff
    """
)
```

## Testing Your Training

Ask these questions to test:
- "List all staff" → Should query Firebase
- "Show drops" → Should query PostgreSQL  
- "Employee names" → Should query Firebase
- "Project details" → Should query PostgreSQL

## Why This Approach?

1. **Scalable**: Add new databases easily
2. **Maintainable**: Clear routing rules
3. **Accurate**: Agent learns your specific schema
4. **Fast**: Routes directly to correct database