# FF_Agent - Natural Language SQL Query Agent for FibreFlow

An AI-powered agent that converts natural language questions into SQL queries for the FibreFlow telecommunications database.

## 🚀 Features

- **Natural Language to SQL**: Ask questions in plain English, get accurate SQL queries
- **Web Interface**: Clean, responsive UI for easy interaction
- **RESTful API**: FastAPI backend for integration with other systems
- **Real-time Results**: Instant query execution against Neon PostgreSQL
- **Production Ready**: Uses Gemini 1.5 Flash for fast, accurate SQL generation

## 📊 Current Database Stats

- **Projects**: 5 (Lawley, Ivory Park, Mamelodi, Mohadin, Hein Test)
- **Drops**: 23,707 customer connections
- **Poles**: 4,471 infrastructure poles
- **Nokia Units**: 327 active devices

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **AI Model**: Google Gemini 1.5 Flash
- **Database**: Neon PostgreSQL
- **Frontend**: React (standalone HTML)
- **Optional**: Vanna AI for advanced learning

## 📋 Prerequisites

- Python 3.10+
- Node.js (optional, for serving UI)
- Neon database credentials
- Google AI Studio API key

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/VelocityFibre/FF_Agent.git
cd FF_Agent
```

### 2. Set up Python virtual environment

```bash
# Install venv if needed
sudo apt install python3-venv

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
```env
# Neon Database
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Google Gemini API
GOOGLE_AI_STUDIO_API_KEY=your-gemini-api-key

# Optional: Firebase
FIREBASE_PROJECT_ID=your-project-id
```

### 5. Test the connection

```bash
python test_connection.py
```

## 🚀 Running the Application

### Option 1: API + Web UI (Recommended)

**Terminal 1 - Start API:**
```bash
source venv/bin/activate
python api.py
```
The API will run on http://localhost:8000

**Terminal 2 - Serve UI:**
```bash
cd ui
python3 -m http.server 3000
```
Open http://localhost:3000 in your browser

### Option 2: Command Line Interface

```bash
source venv/bin/activate
python main.py
```

### Option 3: Direct Python Usage

```python
from ff_agent_gemini import FF_Agent_Gemini

agent = FF_Agent_Gemini()
result = agent.query("How many drops are in the system?")
print(result)
```

## 📝 Example Queries

Try these queries in the UI or CLI:

- "How many drops are in the system?"
- "Show all projects with their creation dates"
- "What's the status breakdown of all poles?"
- "List the top 10 poles with the most drops"
- "How many drops are in the Lawley project?"
- "Show active Nokia equipment"

## 🔌 API Endpoints

- `GET /` - Health check
- `POST /query` - Execute natural language query
- `GET /schema` - Get database schema
- `GET /stats` - Get database statistics

### Example API Usage

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many drops are in the system?"}'
```

## 🏗️ Project Structure

```
FF_Agent/
├── api.py              # FastAPI backend
├── ff_agent_gemini.py  # Main agent using Gemini
├── ff_agent_vanna.py   # Vanna AI implementation
├── main.py             # CLI interface
├── test_connection.py  # Database connection tester
├── ui/
│   └── index.html     # React web interface
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
└── README.md          # This file
```

## 🔒 Security Notes

- Never commit `.env` files or credentials
- Use read-only database users when possible
- The agent validates SQL to prevent dangerous operations
- CORS is configured for development - restrict in production

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Database connection errors
```bash
# Test connection
python test_connection.py

# Check your .env file has correct credentials
cat .env
```

### API not accessible
```bash
# Check if port 8000 is available
lsof -i :8000

# Try a different port
uvicorn api:app --port 8080
```

## 📈 Performance

- Average query response time: 1-3 seconds
- Handles datasets with 20,000+ rows
- Gemini 1.5 Flash provides fast inference
- Results limited to 100 rows by default

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

Property of VelocityFibre

## 👥 Support

For issues or questions:
- Create an issue on GitHub
- Contact: louis@velocityfibre.com

## 🎯 Roadmap

- [ ] Add query caching with Redis
- [ ] Implement user authentication
- [ ] Add data visualization charts
- [ ] Support for complex JOIN queries
- [ ] Export results to CSV/Excel
- [ ] Deploy to Firebase Hosting

---

Built with ❤️ for FibreFlow by VelocityFibre Team