# FF_Agent - AI Database Query Agent

Query your Neon PostgreSQL and Firebase databases using natural language.

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Add Firebase credentials:**
- Download your Firebase service account JSON
- Save as `firebase-credentials.json` in this directory

## Usage

```bash
python main.py
```

## Example Queries

- "Show me all users who signed up last month"
- "What's the total revenue this quarter?"
- "Get all pending orders from Firebase"
- "Show top 10 customers by purchase value"

## Features

- **Natural language queries** - No SQL knowledge needed
- **Dual database support** - Neon (PostgreSQL) and Firebase
- **Context awareness** - Remembers previous queries
- **Safety validation** - Blocks dangerous operations
- **Auto-routing** - Automatically selects the right database