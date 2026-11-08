import ast
import operator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from app.tools.web_search import search_web as perform_web_search

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.models.entities import SupportTicket, ToolCall, User
from app.services.rag import rag_service


class ToolError(Exception):
    pass


class EmptyArgs(BaseModel):
    pass


class CalculatorArgs(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class SearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class TicketArgs(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=4000)


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ToolError("Exponent too large")
        return OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](safe_eval(node.operand))
    raise ToolError("Only basic arithmetic is allowed")


def get_current_time(db: Session, user: User, args: EmptyArgs) -> dict:
    now = datetime.now(timezone.utc)
    return {"utc_iso": now.isoformat(), "readable": now.strftime("%A, %d %B %Y, %H:%M UTC")}


def calculator(db: Session, user: User, args: CalculatorArgs) -> dict:
    try:
        value = safe_eval(ast.parse(args.expression.replace("^", "**"), mode="eval"))
    except ZeroDivisionError:
        raise ToolError("Division by zero")
    except SyntaxError:
        raise ToolError("Invalid expression")
    return {"expression": args.expression, "result": value}


def search_knowledge_base(db: Session, user: User, args: SearchArgs) -> dict:
    hits = rag_service.search(db, user, args.query)
    return {"matches": hits, "count": len(hits)}

def web_search_tool(db: Session, user: User, args: SearchArgs) -> dict:
    try:
        return perform_web_search(args.query)
    except Exception as exc:
        raise ToolError("Web search is temporarily unavailable") from exc

def get_customer_information(db: Session, user: User, args: EmptyArgs) -> dict:
    return {
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "member_since": user.created_at.isoformat(),
    }


def create_support_ticket(db: Session, user: User, args: TicketArgs) -> dict:
    ticket = SupportTicket(user_id=user.id, subject=args.subject, description=args.description)
    db.add(ticket)
    db.commit()
    return {"ticket_id": ticket.id, "status": ticket.status, "subject": ticket.subject}


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    func: Callable[[Session, User, Any], dict]
    roles: tuple[str, ...] = ("USER", "ADMIN", "SUPPORT_AGENT")

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool("get_current_time", "Get the current date and time in UTC", EmptyArgs, get_current_time),
        Tool("calculator", "Evaluate a basic arithmetic expression", CalculatorArgs, calculator),
        Tool("search_knowledge_base", "Search the user's uploaded documents", SearchArgs, search_knowledge_base),
        Tool("get_customer_information", "Get the signed-in user's profile", EmptyArgs, get_customer_information),
        Tool("create_support_ticket", "Open a support ticket for the user", TicketArgs, create_support_ticket),
    ]
}


def list_tools() -> list[dict]:
    return [{"name": t.name, "description": t.description, "parameters": t.args_model.model_json_schema()} for t in TOOLS.values()]


def run_tool(db: Session, user: User, name: str, arguments: dict) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolError(f"Unknown tool: {name}")
    if user.role not in tool.roles:
        raise ToolError("You are not allowed to use this tool")
    success, result = True, {}
    try:
        args = tool.args_model(**(arguments or {}))
        result = tool.func(db, user, args)
    except ValidationError as exc:
        success, result = False, {"error": "Invalid arguments", "details": exc.errors(include_url=False, include_context=False)}
    except ToolError as exc:
        success, result = False, {"error": str(exc)}
    except Exception:
        db.rollback()
        success, result = False, {"error": "Tool failed unexpectedly"}
    db.add(ToolCall(user_id=user.id, tool_name=name, arguments=arguments or {}, result=_jsonable(result), success=success))
    db.commit()
    return {"success": success, "result": result}


def _jsonable(value: Any) -> Any:
    import json

    return json.loads(json.dumps(value, default=str))
