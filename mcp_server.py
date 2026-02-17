"""
MCP Server for Polish Football Players Abroad Tracker (SaaS)

This server provides MCP tools for querying football statistics via FastAPI backend.
Designed for commercial SaaS deployment - secure, scalable, production-ready.

Usage:
    python mcp_server.py

Configuration:
    Create .mcp_config file with:
        API_BASE_URL=http://localhost:8000
        API_KEY=your_api_key  # Optional, for future SaaS authentication
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION (SECURE - No credentials in files)
# ============================================================================

# For local development - connects to your FastAPI backend
# For production - set MCP_API_URL environment variable to your production URL
# Example: export MCP_API_URL=https://your-app.onrender.com

API_BASE_URL = os.getenv("MCP_API_URL", "http://localhost:8000")

# Optional: API Key for SaaS authentication (set via environment variable only)
# Never hardcode API keys in source code for commercial projects
API_KEY = os.getenv("MCP_API_KEY")

# Request timeout
TIMEOUT = 30.0

logger.info(f"MCP Server initialized")
logger.info(f"API Base URL: {API_BASE_URL}")
logger.info(f"API Key: {'configured' if API_KEY else 'none'}")
logger.info("SECURE: No credentials stored in files")


# ============================================================================
# HTTP CLIENT
# ============================================================================

class APIClient:
    """HTTP client for FastAPI backend"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to API"""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def post(self, endpoint: str, data: dict = None) -> dict:
        """Make POST request to API"""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
            return response.json()


api = APIClient(API_BASE_URL, API_KEY)


# ============================================================================
# MCP SERVER
# ============================================================================

server = Server("polish-football-tracker")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="list_players",
            description="Get list of all tracked Polish players abroad with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Filter by player name (partial match)"},
                    "team": {"type": "string", "description": "Filter by team name (partial match)"},
                    "league": {"type": "string", "description": "Filter by league name (partial match)"},
                    "limit": {"type": "integer", "description": "Max results (default: 100, max: 1000)", "default": 100},
                    "offset": {"type": "integer", "description": "Pagination offset (default: 0)", "default": 0}
                }
            }
        ),
        Tool(
            name="get_player",
            description="Get detailed information about a specific player by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "integer",
                        "description": "Player ID (you can find it using list_players first)"
                    }
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="get_player_stats",
            description="Get competition statistics (goals, assists, xG, cards, etc.) for a player",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer", "description": "Player ID"},
                    "season": {"type": "string", "description": "Season filter (e.g., '2025-2026')"},
                    "competition_type": {
                        "type": "string",
                        "description": "Competition type filter",
                        "enum": ["LEAGUE", "EUROPEAN_CUPS", "NATIONAL_TEAM", "DOMESTIC_CUPS"]
                    },
                    "limit": {"type": "integer", "description": "Max results (default: 200)", "default": 200},
                    "offset": {"type": "integer", "description": "Pagination offset", "default": 0}
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="get_goalkeeper_stats",
            description="Get goalkeeper statistics (saves, clean sheets, goals against) for a player",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer", "description": "Player ID"},
                    "season": {"type": "string", "description": "Season filter (e.g., '2025-2026')"},
                    "competition_type": {
                        "type": "string",
                        "description": "Competition type filter",
                        "enum": ["LEAGUE", "EUROPEAN_CUPS", "NATIONAL_TEAM", "DOMESTIC_CUPS"]
                    },
                    "limit": {"type": "integer", "description": "Max results (default: 200)", "default": 200},
                    "offset": {"type": "integer", "description": "Pagination offset", "default": 0}
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="get_match_logs",
            description="Get detailed match-by-match performance logs for a player",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer", "description": "Player ID"},
                    "season": {"type": "string", "description": "Filter by season"},
                    "competition": {"type": "string", "description": "Filter by competition name"}
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="compare_players",
            description="Compare statistics between two players side-by-side",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id_1": {"type": "integer", "description": "First player ID"},
                    "player_id_2": {"type": "integer", "description": "Second player ID"},
                    "season": {"type": "string", "description": "Season to compare (default: current)"},
                    "competition_type": {
                        "type": "string",
                        "description": "Filter by competition type",
                        "enum": ["LEAGUE", "EUROPEAN_CUPS", "NATIONAL_TEAM", "DOMESTIC_CUPS"]
                    }
                },
                "required": ["player_id_1", "player_id_2"]
            }
        ),
        Tool(
            name="search_player",
            description="Search for a specific player by name in the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name to search (will be used with list_players filter)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_leagues",
            description="Get list of all leagues where Polish players currently play",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="sync_player",
            description="Trigger manual sync of a specific player from RapidAPI (admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {"type": "integer", "description": "Player ID to sync"}
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="health_check",
            description="Check if the API backend is operational",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle MCP tool calls"""

    try:
        if name == "list_players":
            params = {
                "limit": min(arguments.get("limit", 100), 1000),
                "offset": arguments.get("offset", 0)
            }
            if name_filter := arguments.get("name"):
                params["name"] = name_filter
            if team := arguments.get("team"):
                params["team"] = team
            if league := arguments.get("league"):
                params["league"] = league

            result = await api.get("/api/players/", params=params)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_player":
            player_id = arguments["player_id"]
            result = await api.get(f"/api/players/{player_id}")
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_player_stats":
            player_id = arguments["player_id"]
            params = {
                "player_id": player_id,
                "limit": min(arguments.get("limit", 200), 1000),
                "offset": arguments.get("offset", 0)
            }
            if season := arguments.get("season"):
                params["season"] = season
            if comp_type := arguments.get("competition_type"):
                params["competition_type"] = comp_type

            result = await api.get("/api/players/stats/competition", params=params)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_goalkeeper_stats":
            player_id = arguments["player_id"]
            params = {
                "player_id": player_id,
                "limit": min(arguments.get("limit", 200), 1000),
                "offset": arguments.get("offset", 0)
            }
            if season := arguments.get("season"):
                params["season"] = season
            if comp_type := arguments.get("competition_type"):
                params["competition_type"] = comp_type

            result = await api.get("/api/players/stats/goalkeeper", params=params)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_match_logs":
            player_id = arguments["player_id"]
            params = {"player_id": player_id}
            if season := arguments.get("season"):
                params["season"] = season
            if competition := arguments.get("competition"):
                params["competition"] = competition

            result = await api.get(f"/api/matchlogs/{player_id}", params=params)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "compare_players":
            player_id_1 = arguments["player_id_1"]
            player_id_2 = arguments["player_id_2"]
            params = {
                "player_id_1": player_id_1,
                "player_id_2": player_id_2
            }
            if season := arguments.get("season"):
                params["season"] = season
            if comp_type := arguments.get("competition_type"):
                params["competition_type"] = comp_type

            result = await api.get("/api/comparison/compare", params=params)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "search_player":
            name = arguments["name"]
            # Use list_players with name filter
            result = await api.get("/api/players/", params={"name": name, "limit": 50})
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_leagues":
            # Get all players and extract unique leagues
            result = await api.get("/api/players/", params={"limit": 1000})
            leagues = sorted(set(p.get("league", "Unknown") for p in result))
            return [TextContent(
                type="text",
                text=json.dumps({"leagues": leagues, "count": len(leagues)}, indent=2)
            )]

        elif name == "sync_player":
            player_id = arguments["player_id"]
            result = await api.post(f"/api/sync-player/{player_id}")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "health_check":
            result = await api.get("/health")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"API error: {e.response.status_code}",
                "detail": e.response.text,
                "tool": name
            })
        )]
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e), "tool": name})
        )]


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="polish-football-tracker",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
