"""
Vector Database Monitoring Dashboard
Real-time monitoring and analytics for vector database performance
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from vector_store_cached import CachedVectorStore

load_dotenv()

app = FastAPI(title="Vector DB Monitor")
vector_store = CachedVectorStore()

def get_metrics() -> Dict:
    """Gather comprehensive metrics"""
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'database': {},
        'cache': {},
        'performance': {},
        'quality': {}
    }
    
    try:
        with vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                # Database metrics
                cur.execute("SELECT COUNT(*) FROM query_embeddings")
                metrics['database']['total_patterns'] = cur.fetchone()[0]
                
                cur.execute("SELECT AVG(success_rate) FROM query_embeddings")
                avg_success = cur.fetchone()[0]
                metrics['database']['avg_success_rate'] = float(avg_success) if avg_success else 0
                
                cur.execute("SELECT COUNT(*) FROM error_patterns WHERE resolved = FALSE")
                metrics['database']['unresolved_errors'] = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(*) FROM query_embeddings 
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                """)
                metrics['database']['patterns_24h'] = cur.fetchone()[0]
                
                # Top patterns
                cur.execute("""
                    SELECT question, execution_count, success_rate
                    FROM query_embeddings
                    ORDER BY execution_count DESC
                    LIMIT 5
                """)
                metrics['database']['top_patterns'] = [
                    {'question': row[0][:50], 'count': row[1], 'success': row[2]}
                    for row in cur.fetchall()
                ]
    except Exception as e:
        metrics['database']['error'] = str(e)
    
    # Cache metrics
    cache_stats = vector_store.get_cache_stats()
    metrics['cache'] = cache_stats
    
    # Performance tracking
    test_queries = ["Show all data", "Count records", "Find by status"]
    response_times = []
    
    for query in test_queries:
        start = time.time()
        vector_store.find_similar_queries_fast(query, limit=1)
        response_times.append(time.time() - start)
    
    metrics['performance']['avg_response_time'] = sum(response_times) / len(response_times)
    metrics['performance']['max_response_time'] = max(response_times)
    
    return metrics

@app.get("/metrics")
async def get_current_metrics():
    """Get current metrics as JSON"""
    return get_metrics()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Interactive monitoring dashboard"""
    metrics = get_metrics()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vector DB Monitor</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                margin: 0;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 30px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
                background: rgba(255, 255, 255, 0.15);
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: bold;
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 0.9em;
                opacity: 0.9;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .status-good {{ color: #4ade80; }}
            .status-warning {{ color: #facc15; }}
            .status-error {{ color: #f87171; }}
            .chart {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                margin-top: 20px;
            }}
            .top-patterns {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                margin-top: 20px;
            }}
            .pattern-item {{
                display: flex;
                justify-content: space-between;
                padding: 10px;
                margin: 5px 0;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }}
            .refresh-time {{
                text-align: center;
                opacity: 0.7;
                margin-top: 20px;
            }}
        </style>
        <meta http-equiv="refresh" content="30">
    </head>
    <body>
        <div class="container">
            <h1>🚀 Vector Database Monitor</h1>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Patterns</div>
                    <div class="metric-value">{metrics['database'].get('total_patterns', 0)}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-value {('status-good' if metrics['database'].get('avg_success_rate', 0) > 0.8 else 'status-warning')}">
                        {metrics['database'].get('avg_success_rate', 0):.1%}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Cache Hit Rate</div>
                    <div class="metric-value status-good">{metrics['cache'].get('hit_rate', '0%')}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Avg Response Time</div>
                    <div class="metric-value {('status-good' if metrics['performance'].get('avg_response_time', 1) < 0.5 else 'status-warning')}">
                        {metrics['performance'].get('avg_response_time', 0):.3f}s
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Patterns (24h)</div>
                    <div class="metric-value">{metrics['database'].get('patterns_24h', 0)}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Unresolved Errors</div>
                    <div class="metric-value {('status-error' if metrics['database'].get('unresolved_errors', 0) > 10 else 'status-good')}">
                        {metrics['database'].get('unresolved_errors', 0)}
                    </div>
                </div>
            </div>
            
            <div class="top-patterns">
                <h2>🔥 Top Query Patterns</h2>
                {''.join([
                    f'<div class="pattern-item">'
                    f'<span>{p["question"]}...</span>'
                    f'<span>Used {p["count"]}x | {p["success"]:.0%}</span>'
                    f'</div>'
                    for p in metrics['database'].get('top_patterns', [])
                ])}
            </div>
            
            <div class="chart">
                <h2>📊 System Health</h2>
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <div style="font-size: 3em;">{'✅' if metrics['database'].get('avg_success_rate', 0) > 0.7 else '⚠️'}</div>
                        <div>Query Success</div>
                    </div>
                    <div>
                        <div style="font-size: 3em;">{'✅' if float(metrics['cache'].get('hit_rate', '0%').replace('%', '')) > 50 else '⚠️'}</div>
                        <div>Cache Performance</div>
                    </div>
                    <div>
                        <div style="font-size: 3em;">{'✅' if metrics['performance'].get('avg_response_time', 1) < 1 else '⚠️'}</div>
                        <div>Response Speed</div>
                    </div>
                </div>
            </div>
            
            <div class="refresh-time">
                Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh in 30s
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        with vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Vector DB Monitor on http://localhost:8001")
    print("📊 Dashboard: http://localhost:8001")
    print("📈 Metrics API: http://localhost:8001/metrics")
    uvicorn.run(app, host="0.0.0.0", port=8001)