"""POST /agent/query -- tick-data agent se sawaal poochho.
Role authenticated session se aata hai (yahan demo ke liye X-Role header).
Jaan-boojh ke JSON body se NAHI liya -- taaki caller khud ko 'quant' bana ke
escalate na kar sake."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .agent import run_agent
from .roles import get_role

router = APIRouter(prefix="/agent", tags=["agent"])


class Query(BaseModel):
    question: str


def make_router(execute):
    """execute: async fn(sql)->list[dict]. main.py apna asyncpg pool inject karega."""

    @router.post("/query")
    async def query(body: Query, x_role: str = Header(default="viewer")):
        try:
            role = get_role(x_role)
        except ValueError:
            raise HTTPException(403, "unknown role")
        result = await run_agent(body.question, role, execute)
        return {
            "answer": result.answer,
            "tool_calls": result.tool_calls,
            "usage": result.usage,
            "trace": result.trace,   # latency/token/cost per turn -> UI dashboard
        }

    return router
