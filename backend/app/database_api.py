"""Database API endpoints for JARVIS."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database_service import database_service

router = APIRouter(prefix="/api/database", tags=["database"])


class DatabaseConnectRequest(BaseModel):
    connection_string: str


class DatabaseConnectSQLiteRequest(BaseModel):
    db_path: str


class DatabaseQueryRequest(BaseModel):
    query: str
    params: Optional[dict] = None


class DatabaseBackupRequest(BaseModel):
    table_name: str
    backup_suffix: str = "_backup"


@router.post("/connect")
async def connect_to_database(req: DatabaseConnectRequest):
    """Connect to a database using a connection string."""
    result = database_service.connect(req.connection_string)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/connect/sqlite")
async def connect_to_sqlite(req: DatabaseConnectSQLiteRequest):
    """Connect to a SQLite database."""
    result = database_service.connect_sqlite(req.db_path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/disconnect")
async def disconnect_from_database():
    """Disconnect from the database."""
    return database_service.disconnect()


@router.get("/status")
async def get_connection_status():
    """Get database connection status."""
    return {
        "connected": database_service.is_connected(),
        "database_type": database_service.database_type,
    }


@router.get("/schema")
async def get_database_schema():
    """Get database schema information."""
    result = database_service.get_schema()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/query")
async def execute_query(req: DatabaseQueryRequest):
    """Execute a SQL query."""
    result = database_service.execute_query(req.query, req.params)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Query failed"))
    return result


@router.post("/query/safe")
async def execute_safe_query(req: DatabaseQueryRequest):
    """Execute a SQL query with safety checks."""
    result = database_service.execute_safe_query(req.query, req.params)
    if not result["success"]:
        if result.get("requires_confirmation"):
            raise HTTPException(
                status_code=403,
                detail=f"{result['error']}. This operation requires explicit confirmation.",
            )
        raise HTTPException(status_code=400, detail=result.get("error", "Query failed"))
    return result


@router.post("/analyze")
async def analyze_query_result(req: DatabaseQueryRequest):
    """Execute a query and analyze the results."""
    query_result = database_service.execute_query(req.query, req.params)
    if not query_result["success"]:
        raise HTTPException(status_code=400, detail=query_result.get("error", "Query failed"))

    analysis = database_service.analyze_query_result(query_result)
    return {
        "query_result": query_result,
        "analysis": analysis,
    }


@router.get("/table/{table_name}/count")
async def get_table_row_count(table_name: str):
    """Get the number of rows in a table."""
    result = database_service.get_table_row_count(table_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/backup")
async def backup_table(req: DatabaseBackupRequest):
    """Create a backup of a table."""
    result = database_service.backup_table(req.table_name, req.backup_suffix)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/databases")
async def list_databases():
    """List all databases."""
    result = database_service.list_databases()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
