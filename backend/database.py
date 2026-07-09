import sqlite3
import os

DB_NAME = "maestro.db"

def init_db():
    # Establish connection to the SQLite database (creates the file if it doesn't exist)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create the 'agents' table to store canvas node data, agent states, and hierarchical relationships
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            parent_agent_id TEXT DEFAULT '0',
            status TEXT DEFAULT 'idle',
            position_x REAL DEFAULT 0.0,
            position_y REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'messages' table to store the conversation history and reasoning traces for each agent
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE
        )
    ''')

    # Create an index on the agent_id foreign key to optimize message retrieval performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_messages ON messages(agent_id)')

    conn.commit()
    conn.close()
    
    print("Database schema initialized successfully.")

if __name__ == "__main__":
    init_db()