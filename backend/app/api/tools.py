from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.tools.registry import TOOLS, list_tools, run_tool

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def available_tools(user: User = Depends(get_current_user)):
    return list_tools()


@router.post("/{tool_name}")
def execute(tool_name: str, arguments: dict | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if tool_name not in TOOLS:
        raise HTTPException(404, "Tool not found")
    outcome = run_tool(db, user, tool_name, arguments or {})
    if not outcome["success"]:
        raise HTTPException(400, outcome["result"])
    return outcome["result"]
