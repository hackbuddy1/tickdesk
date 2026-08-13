from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .agent import run_agent
from .roles import get_role

router = APIRouter(prefix="/agent", tags=["agent"])


class Query(BaseModel):
    question: str

def make_router(execute):

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
            "trace": result.trace,   
        }

    return router
