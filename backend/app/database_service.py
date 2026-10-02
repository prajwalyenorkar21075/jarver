"""SQL Database service for JARVIS - connection, query execution, and analysis."""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("jarvis.database_service")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseService:
    """Handles database connections and query execution."""

    def __init__(self):
        self.engine: Optional[Engine] = None
        self.connection_url: Optional[str] = None
        self.database_type: Optional[str] = None

    @staticmethod
    def _validate_table_name(engine: Engine, table_name: str) -> str:
        """Validate a table identifier against the regex and live schema allowlist.

        Raises ValueError on rejection; callers surface it as an error response.
        Table names cannot be parameter-bound in SQL, so this allowlist is the
        protection against injection through identifier positions.
        """
        if not isinstance(table_name, str) or not _IDENTIFIER_RE.match(table_name):
            raise ValueError(
                f"Invalid table name: must match [A-Za-z_][A-Za-z0-9_]* (got {table_name!r})"
            )
        try:
            existing = set(inspect(engine).get_table_names())
        except Exception as e:
            raise ValueError(f"Could not verify table names against database: {e}")
        if table_name not in existing:
            raise ValueError(
                f"Table '{table_name}' does not exist in the connected database."
            )
        return table_name

    def connect(self, connection_string: str) -> dict:
        """Connect to a database using a connection string."""
        try:
            # Parse connection string to determine database type
            parsed = urlparse(connection_string)
            self.database_type = parsed.scheme

            # Create engine
            self.engine = create_engine(connection_string, echo=False)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.connection_url = connection_string

            return {
                "success": True,
                "database_type": self.database_type,
                "message": f"Connected to {self.database_type} database successfully",
            }
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            return {"success": False, "error": f"Connection failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            return {"success": False, "error": str(e)}

    def connect_sqlite(self, db_path: str) -> dict:
        """Connect to a SQLite database."""
        connection_string = f"sqlite:///{db_path}"
        return self.connect(connection_string)

    def disconnect(self) -> dict:
        """Disconnect from the database."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.connection_url = None
            self.database_type = None
            return {"success": True, "message": "Disconnected from database"}
        return {"success": False, "error": "No active connection"}

    def is_connected(self) -> bool:
        """Check if there's an active database connection."""
        if not self.engine:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_schema(self) -> dict:
        """Get database schema information."""
        if not self.engine:
            return {"success": False, "error": "No active database connection"}

        try:
            inspector = inspect(self.engine)
            schema = {
                "success": True,
                "database_type": self.database_type,
                "tables": [],
            }

            for table_name in inspector.get_table_names():
                table_info = {
                    "name": table_name,
                    "columns": [],
                    "primary_key": [],
                    "foreign_keys": [],
                    "indexes": [],
                }

                # Get columns
                for column in inspector.get_columns(table_name):
                    table_info["columns"].append(
                        {
                            "name": column["name"],
                            "type": str(column["type"]),
                            "nullable": column["nullable"],
                            "default": column["default"],
                        }
                    )

                # Get primary key
                pk = inspector.get_pk_constraint(table_name)
                if pk and "constrained_columns" in pk:
                    table_info["primary_key"] = pk["constrained_columns"]

                # Get foreign keys
                fks = inspector.get_foreign_keys(table_name)
                for fk in fks:
                    table_info["foreign_keys"].append(
                        {
                            "columns": fk["constrained_columns"],
                            "referenced_table": fk["referred_table"],
                            "referenced_columns": fk["referred_columns"],
                        }
                    )

                # Get indexes
                indexes = inspector.get_indexes(table_name)
                for index in indexes:
                    table_info["indexes"].append(
                        {
                            "name": index["name"],
                            "columns": index["column_names"],
                            "unique": index["unique"],
                        }
                    )

                schema["tables"].append(table_info)

            return schema
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {"success": False, "error": str(e)}

    def execute_query(self, query: str, params: Optional[dict] = None) -> dict:
        """Execute a SQL query and return results."""
        if not self.engine:
            return {"success": False, "error": "No active database connection"}

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})

                # Check if query returns results
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())

                    # Convert rows to list of dicts
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert non-serializable types
                            if hasattr(value, "__dict__"):
                                value = str(value)
                            row_dict[col] = value
                        data.append(row_dict)

                    return {
                        "success": True,
                        "columns": columns,
                        "data": data,
                        "row_count": len(data),
                        "query": query,
                    }
                else:
                    # Query doesn't return rows (INSERT, UPDATE, DELETE)
                    conn.commit()
                    return {
                        "success": True,
                        "message": f"Query executed successfully. Rows affected: {result.rowcount}",
                        "rows_affected": result.rowcount,
                        "query": query,
                    }
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            return {"success": False, "error": f"Query failed: {str(e)}", "query": query}
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            return {"success": False, "error": str(e), "query": query}

    def execute_safe_query(self, query: str, params: Optional[dict] = None) -> dict:
        """Execute a query with safety checks (prevents dangerous operations without confirmation)."""
        query_upper = query.strip().upper()

        # Check for dangerous operations
        dangerous_keywords = ["DROP ", "TRUNCATE ", "ALTER ", "DELETE ", "UPDATE "]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "success": False,
                    "error": f"Dangerous operation detected: {keyword.strip()}. Use execute_query with explicit confirmation.",
                    "requires_confirmation": True,
                    "query": query,
                }

        return self.execute_query(query, params)

    def get_table_row_count(self, table_name: str) -> dict:
        """Get the number of rows in a table."""
        if not self.engine:
            return {"success": False, "error": "No active database connection"}
        try:
            table_name = self._validate_table_name(self.engine, table_name)
        except ValueError as e:
            return {"success": False, "error": str(e)}
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query)

        if result["success"] and result["data"]:
            return {
                "success": True,
                "table": table_name,
                "row_count": result["data"][0]["count"],
            }
        return result

    def analyze_query_result(self, query_result: dict) -> dict:
        """Analyze query results and provide insights."""
        if not query_result.get("success") or "data" not in query_result:
            return {"success": False, "error": "Invalid query result"}

        data = query_result["data"]
        if not data:
            return {"success": True, "analysis": "No data to analyze", "row_count": 0}

        analysis = {
            "success": True,
            "row_count": len(data),
            "columns": query_result.get("columns", []),
            "statistics": {},
        }

        # Analyze numeric columns
        for col in analysis["columns"]:
            values = [row[col] for row in data if col in row and row[col] is not None]

            # Check if column is numeric
            if values and all(isinstance(v, (int, float)) for v in values[:10]):
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    analysis["statistics"][col] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                        "sum": sum(numeric_values),
                        "count": len(numeric_values),
                    }

        return analysis

    def backup_table(self, table_name: str, backup_suffix: str = "_backup") -> dict:
        """Create a backup of a table."""
        if not self.engine:
            return {"success": False, "error": "No active database connection"}

        try:
            table_name = self._validate_table_name(self.engine, table_name)
            if not re.match(r"^[A-Za-z0-9_]*$", backup_suffix):
                raise ValueError(
                    f"Invalid backup suffix: must match [A-Za-z0-9_]* (got {backup_suffix!r})"
                )
            backup_table = f"{table_name}{backup_suffix}"
            if not _IDENTIFIER_RE.match(backup_table):
                raise ValueError(f"Invalid backup table name: {backup_table!r}")
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            with self.engine.connect() as conn:
                # Drop backup table if exists
                conn.execute(text(f"DROP TABLE IF EXISTS {backup_table}"))

                # Create backup
                if self.database_type == "sqlite":
                    conn.execute(
                        text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
                    )
                else:
                    # For other databases, use CREATE TABLE ... AS SELECT
                    conn.execute(
                        text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
                    )

                conn.commit()

            return {
                "success": True,
                "original_table": table_name,
                "backup_table": backup_table,
                "message": f"Table {table_name} backed up to {backup_table}",
            }
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"success": False, "error": str(e)}

    def list_databases(self) -> dict:
        """List all databases (for servers that support multiple databases)."""
        if not self.engine:
            return {"success": False, "error": "No active database connection"}

        try:
            with self.engine.connect() as conn:
                if self.database_type == "postgresql":
                    result = conn.execute(
                        text("SELECT datname FROM pg_database WHERE datistemplate = false")
                    )
                elif self.database_type == "mysql":
                    result = conn.execute(text("SHOW DATABASES"))
                elif self.database_type == "sqlite":
                    # SQLite has only one database
                    return {
                        "success": True,
                        "databases": ["main"],
                        "database_type": self.database_type,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Listing databases not supported for {self.database_type}",
                    }

                databases = [row[0] for row in result.fetchall()]
                return {
                    "success": True,
                    "databases": databases,
                    "database_type": self.database_type,
                }
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            return {"success": False, "error": str(e)}


# Global instance
database_service = DatabaseService()
