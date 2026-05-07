"""
Tool implementations for GeekBrain AI System.

This module provides tools for querying databases and monitoring APIs.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
import sqlite3
import requests


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by the LLM."""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolResult:
    """Result from executing a tool."""
    success: bool
    data: Any
    error: str = None


class DatabaseQueryTool:
    """Tool for executing read-only SQL queries against the database."""
    
    def __init__(self, db_path: str):
        """
        Initialize database query tool.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.read_only_keywords = ['SELECT', 'WITH']
        self.forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER']
    
    def execute_query(self, sql: str) -> ToolResult:
        """
        Execute read-only SQL query against database.
        
        Args:
            sql: SQL query string
            
        Returns:
            ToolResult with rows or error message
        """
        # Validate query is read-only
        sql_upper = sql.strip().upper()
        if not any(sql_upper.startswith(kw) for kw in self.read_only_keywords):
            return ToolResult(
                success=False,
                data=None,
                error="Only SELECT queries are allowed"
            )
        
        if any(kw in sql_upper for kw in self.forbidden_keywords):
            return ToolResult(
                success=False,
                data=None,
                error="Write operations are not permitted"
            )
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return ToolResult(success=True, data=rows)
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Query execution failed: {str(e)}"
            )
    
    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM."""
        return ToolDefinition(
            name="query_database",
            description=(
                "Execute SQL query against structured database. "
                "Use for HISTORICAL data: monthly costs, incident history, "
                "SLA targets, daily metrics from Jan-Mar 2026. "
                "Returns rows as list of dictionaries."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    }
                },
                "required": ["sql"]
            }
        )


class ServiceMetricsTool:
    """Tool for fetching current service metrics from monitoring API."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize service metrics tool.
        
        Args:
            api_base_url: Base URL of monitoring API
        """
        self.api_base_url = api_base_url
        self.timeout = 3  # seconds
    
    def get_metrics(self, service_name: str) -> ToolResult:
        """
        Get current live metrics for a service.
        
        Args:
            service_name: Name of service (e.g., 'PaymentGW')
            
        Returns:
            ToolResult with current metrics or error
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/metrics/{service_name}",
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Service '{service_name}' not found"
                )
            
            response.raise_for_status()
            data = response.json()
            
            return ToolResult(success=True, data=data)
            
        except requests.Timeout:
            return ToolResult(
                success=False,
                data=None,
                error="Monitoring API timeout - service may be down"
            )
        except requests.RequestException as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to fetch metrics: {str(e)}"
            )
    
    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM."""
        return ToolDefinition(
            name="get_service_metrics",
            description=(
                "Get CURRENT live performance metrics for a service. "
                "Use for real-time data: current latency, error rate, "
                "request volume. Returns p50/p95/p99 latency in ms, "
                "error_rate as percentage, requests_per_min."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service (e.g., PaymentGW, NotificationSvc)"
                    }
                },
                "required": ["service_name"]
            }
        )


class ToolExecutor:
    """Orchestrates tool execution."""
    
    def __init__(self, tools: List[Any]):
        """
        Initialize tool executor.
        
        Args:
            tools: List of tool instances
        """
        self.tools = {tool.get_definition().name: tool for tool in tools}
        self.tool_definitions = [tool.get_definition() for tool in tools]
    
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool function with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            ToolResult from tool execution
        """
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not found"
            )
        
        tool = self.tools[tool_name]
        
        # Route to appropriate method based on tool
        if tool_name == "query_database":
            return tool.execute_query(**parameters)
        elif tool_name == "get_service_metrics":
            return tool.get_metrics(**parameters)
        else:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {tool_name}"
            )
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Return list of available tools for LLM."""
        return self.tool_definitions
