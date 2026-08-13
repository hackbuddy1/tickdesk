from __future__ import annotations
from dataclasses import dataclass


@dataclass
class _Text:
    text: str
    type: str = "text"

@dataclass
class _ToolUse:
    id: str
    name: str
    input: dict
    type: str = "tool_use"

@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int

@dataclass
class _Resp:
    content: list
    stop_reason: str
    usage: _Usage


class MockMessages:
    async def create(self, *, model, max_tokens, system, tools, messages):
        tool_names = {t["name"] for t in tools}  
        last = messages[-1]
      
        if isinstance(last.get("content"), list) and \
           any(isinstance(b, dict) and b.get("type") == "tool_result" for b in last["content"]):
            note = _summarize(last["content"])
            return _Resp([_Text(note)], "end_turn", _Usage(120, 40))

        q = _text_of(messages[0]["content"]).lower()

     
        bad = ("drop", "delete", "truncate", "/etc/passwd", "pg_read_file",
               "pg_sleep", "admin", "escalat", "ignore your instructions", "users table")
        if any(b in q for b in bad):
            return _Resp(
                [_Text("I can't do that. I only run read-only queries on the "
                       "tables I'm allowed to access, and I won't change my role "
                       "or touch anything outside them.")],
                "end_turn", _Usage(80, 30))

      
        if ("schema" in q or "column" in q) and "get_schema" in tool_names:
            return _tool("get_schema", {}, tool_names)

        if "run_sql" in tool_names and ("sql" in q or "top" in q or "count" in q
                                        or "group" in q or "join" in q):
            sql = _naive_sql(q)
            return _tool("run_sql", {"sql": sql}, tool_names)

        if "compute_metric" in tool_names:
            metric = ("vwap" if "vwap" in q else
                      "volume" if "volume" in q else
                      "range" if "range" in q or "high" in q else
                      "last_price")
            sym = _guess_symbol(q)
            return _tool("compute_metric",
                         {"metric": metric, "symbol": sym, "window_s": 60},
                         tool_names)

        return _Resp([_Text("I don't have a tool for that request.")],
                     "end_turn", _Usage(60, 20))


class MockAnthropic:
    """AsyncAnthropic ke jagah drop-in."""
    def __init__(self, *a, **k):
        self.messages = MockMessages()


# --- helpers ---
def _tool(name, inp, tool_names):
    if name not in tool_names:  
        return _Resp([_ToolUse("t1", name, inp)], "tool_use", _Usage(90, 25))
    return _Resp([_ToolUse("t1", name, inp)], "tool_use", _Usage(90, 25))

def _text_of(content):
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))

def _guess_symbol(q):
    import re
    stop = {"WHAT","THE","VWAP","FOR","IS","OF","IN","ME","GIVE","GET",
            "SHOW","AND","A","AN","LAST","PRICE","VOLUME","RANGE","SPREAD",
            "AVG","AVERAGE","LATEST","CURRENT","HFT","SQL","TOP"}
   
    for tok in re.findall(r"[A-Za-z]{1,6}", q):
        up = tok.upper()
        if up in stop:
            continue
     
        if tok.isupper() or tok[0].isupper():
            return up
    return "AAPL"

def _naive_sql(q):
    if "top" in q and "volume" in q or "traded size" in q:
        return ("SELECT symbol, sum(size) AS total FROM ticks "
                "GROUP BY symbol ORDER BY total DESC LIMIT 5")
    return "SELECT symbol, price, ts FROM ticks ORDER BY ts DESC LIMIT 10"

def _summarize(tool_results):
    parts = []
    for b in tool_results:
        if isinstance(b, dict) and b.get("type") == "tool_result":
            parts.append(str(b.get("content", "")))
    joined = " | ".join(parts)
    return f"Here's what I found: {joined[:400]}"
