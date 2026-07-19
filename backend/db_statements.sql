CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
CREATE TABLE agents (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	model VARCHAR NOT NULL, 
	system_prompt TEXT, 
	settings JSON NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	error_message TEXT, 
	parent_id TEXT, 
	canvas_x FLOAT NOT NULL, 
	canvas_y FLOAT NOT NULL, 
	created_at INTEGER NOT NULL, 
	updated_at INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_agents_status CHECK (status IN ('idle', 'thinking', 'tool_calling', 'error', 'done', 'queued')), 
	FOREIGN KEY(parent_id) REFERENCES agents (id) ON DELETE SET NULL
);
CREATE INDEX idx_agents_parent ON agents (parent_id);
CREATE TABLE meta (
	"key" VARCHAR NOT NULL, 
	value VARCHAR, 
	PRIMARY KEY ("key")
);
CREATE TABLE messages (
	id VARCHAR NOT NULL, 
	agent_id TEXT NOT NULL, 
	seq INTEGER NOT NULL, 
	role VARCHAR(9) NOT NULL, 
	content TEXT, 
	thinking TEXT, 
	created_at INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE, 
	CONSTRAINT ck_messages_role CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);
CREATE UNIQUE INDEX idx_messages_agent_seq ON messages (agent_id, seq);
CREATE TABLE "runs" (
	id VARCHAR NOT NULL, 
	agent_id TEXT NOT NULL, 
	prompt VARCHAR NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	started_at INTEGER, 
	finished_at INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_runs_status CHECK (status IN ('queued', 'running', 'done', 'error', 'cancelled')), 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE
);
CREATE INDEX idx_runs_agent_started ON runs (agent_id, started_at);
CREATE TABLE tool_calls (
	id VARCHAR NOT NULL, 
	agent_id TEXT NOT NULL, 
	message_id TEXT, 
	tool_name VARCHAR NOT NULL, 
	operation VARCHAR(5) NOT NULL, 
	arguments JSON NOT NULL, 
	result TEXT, 
	status VARCHAR(7) NOT NULL, 
	error_message TEXT, 
	created_at INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE, 
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE SET NULL, 
	CONSTRAINT ck_tool_calls_operation CHECK (operation IN ('read', 'write')), 
	CONSTRAINT ck_tool_calls_status CHECK (status IN ('pending', 'success', 'error'))
);
CREATE INDEX idx_tool_calls_agent ON tool_calls (agent_id);
