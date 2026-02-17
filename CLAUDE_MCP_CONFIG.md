# Claude Desktop MCP Configuration

## Windows

Edit config file at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

## macOS

Edit config file at:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

## Configuration JSON

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "polish-football-tracker": {
      "command": "python",
      "args": [
        "E:/Polish Footballers Abroad Tracker/polish-players-tracker/mcp_server.py"
      ],
      "env": {
        "MCP_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Production URL

When deploying to production (e.g., Render.com), change `MCP_API_URL`:

```json
{
  "mcpServers": {
    "polish-football-tracker": {
      "command": "python",
      "args": [
        "E:/Polish Footballers Abroad Tracker/polish-players-tracker/mcp_server.py"
      ],
      "env": {
        "MCP_API_URL": "https://polish-football-data-hub-international.onrender.com/"
      }
    }
  }
}
```

## For SaaS with API Key (future)

When you add authentication:

```json
{
  "mcpServers": {
    "polish-football-tracker": {
      "command": "python",
      "args": [
        "E:/Polish Footballers Abroad Tracker/polish-players-tracker/mcp_server.py"
      ],
      "env": {
        "MCP_API_URL": "https://your-app.onrender.com",
        "MCP_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

## Installation

1. Install requirements:
```powershell
pip install -r mcp_requirements.txt
```

2. Add config to Claude Desktop (see paths above)

3. Restart Claude Desktop

4. Verify: Ask Claude "List all Polish players" - it should use the MCP tool
