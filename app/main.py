from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Literal, Callable
from uuid import uuid4


# Tool Registry


ToolFn = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
TOOL_REGISTRY: Dict[str, ToolFn] = {}


def register_tool(name: str):
    def decorator(func: ToolFn) -> ToolFn:
        TOOL_REGISTRY[name] = func
        return func
    return decorator



@register_tool("split_text")
def split_text_tool(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    
    text: str = state.get("text", "")
    chunk_size: int = int(config.get("chunk_size", 200))

    words = text.split()
    chunks: List[str] = []
    current: List[str] = []

    for w in words:
        candidate = " ".join(current + [w])
        if len(candidate) > chunk_size and current:
            chunks.append(" ".join(current))
            current = [w]
        else:
            current.append(w)

    if current:
        chunks.append(" ".join(current))

    state["chunks"] = chunks
    return state


@register_tool("summarize_chunks")
def summarize_chunks_tool(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    chunks: List[str] = state.get("chunks", [])
    summary_words: int = int(config.get("summary_words", 30))

    summaries: List[str] = []
    for chunk in chunks:
        words = chunk.split()
        summaries.append(" ".join(words[:summary_words]))

    state["summaries"] = summaries
    return state


@register_tool("merge_summaries")
def merge_summaries_tool(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    
    summaries: List[str] = state.get("summaries", [])
    merged = " ".join(summaries)
    state["merged_summary"] = merged
    state["summary_length"] = len(merged)
    return state


@register_tool("refine_summary")
def refine_summary_tool(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    
    target_length: int = int(config.get("target_length", 400))

    summary: str = state.get("merged_summary", "")
    if len(summary) <= target_length:
        state["final_summary"] = summary
        state["summary_length"] = len(summary)
        return state

    shorter = summary[:target_length]
    last_space = shorter.rfind(" ")
    if last_space > 0:
        shorter = shorter[:last_space]

    state["merged_summary"] = shorter
    state["final_summary"] = shorter
    state["summary_length"] = len(shorter)
    return state



# Pydantic Models


class Condition(BaseModel):
    key: str
    op: Literal["==", "!=", ">", ">=", "<", "<="]
    value: Any


class NodeConfig(BaseModel):
    name: str
    tool: str                 
    config: Dict[str, Any] = {}


class EdgeConfig(BaseModel):
    source: str
    target: str
    condition: Optional[Condition] = None


class GraphCreateRequest(BaseModel):
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    start_node: str


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any] = {}


class StepLog(BaseModel):
    node: str
    tool: str
    state_snapshot: Dict[str, Any]


class GraphRunResponse(BaseModel):
    run_id: str
    final_state: Dict[str, Any]
    log: List[StepLog]


class GraphStateResponse(BaseModel):
    run_id: str
    graph_id: str
    status: Literal["pending", "running", "completed", "failed"]
    current_node: Optional[str]
    state: Dict[str, Any]
    log: List[StepLog]



# Engine Internals


class GraphDefinition(BaseModel):
    id: str
    start_node: str
    nodes: Dict[str, NodeConfig]
    edges: List[EdgeConfig]


class GraphRunInternal(BaseModel):
    run_id: str
    graph_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    current_node: Optional[str] = None
    state: Dict[str, Any] = {}
    log: List[StepLog] = []


GRAPHS: Dict[str, GraphDefinition] = {}
RUNS: Dict[str, GraphRunInternal] = {}


def create_graph(req: GraphCreateRequest) -> str:
    
    node_map = {n.name: n for n in req.nodes}
    if req.start_node not in node_map:
        raise HTTPException(status_code=400, detail="start_node must be one of the node names")

   
    for edge in req.edges:
        if edge.source not in node_map:
            raise HTTPException(status_code=400, detail=f"Unknown source node: {edge.source}")
        if edge.target not in node_map:
            raise HTTPException(status_code=400, detail=f"Unknown target node: {edge.target}")

    graph_id = str(uuid4())
    graph = GraphDefinition(
        id=graph_id,
        start_node=req.start_node,
        nodes=node_map,
        edges=req.edges
    )
    GRAPHS[graph_id] = graph
    return graph_id


def _eval_condition(cond: Optional[Condition], state: Dict[str, Any]) -> bool:
    if cond is None:
        return True
    left = state.get(cond.key, None)
    right = cond.value
    op = cond.op
    try:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
    except TypeError:
    
        return False
    return False


def _next_node(graph: GraphDefinition, current_node: str, state: Dict[str, Any]) -> Optional[str]:
   
    outgoing = [e for e in graph.edges if e.source == current_node]
    for edge in outgoing:
        if _eval_condition(edge.condition, state):
            return edge.target
    return None 


def run_graph(graph_id: str, initial_state: Dict[str, Any]) -> GraphRunInternal:
   
    graph = GRAPHS.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")

    run_id = str(uuid4())
    run = GraphRunInternal(
        run_id=run_id,
        graph_id=graph_id,
        status="running",
        current_node=graph.start_node,
        state=initial_state.copy(),
        log=[]
    )
    RUNS[run_id] = run

    current = graph.start_node
    max_steps = 100  
    steps = 0

    while current is not None and steps < max_steps:
        run.current_node = current
        node_cfg = graph.nodes[current]

        tool = TOOL_REGISTRY.get(node_cfg.tool)
        if not tool:
            run.status = "failed"
            raise HTTPException(status_code=500, detail=f"Tool '{node_cfg.tool}' is not registered")

       
        new_state = tool(run.state, node_cfg.config)

      
        run.log.append(StepLog(node=current, tool=node_cfg.tool, state_snapshot=new_state.copy()))
        run.state = new_state

      
        current = _next_node(graph, current, run.state)
        steps += 1

    if steps >= max_steps and current is not None:
        run.status = "failed"
        raise HTTPException(status_code=500, detail="Max steps exceeded (possible infinite loop)")

    run.current_node = current
    run.status = "completed"
    return run


def get_run_state(run_id: str) -> GraphRunInternal:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run



# Sample Workflow Definition 


def build_graph() -> GraphCreateRequest:
    
    nodes = [
        NodeConfig(name="split", tool="split_text", config={"chunk_size": 250}),
        NodeConfig(name="summarize", tool="summarize_chunks", config={"summary_words": 40}),
        NodeConfig(name="merge", tool="merge_summaries", config={}),
        NodeConfig(name="refine", tool="refine_summary", config={"target_length": 400}),
    ]

    edges = [
        EdgeConfig(source="split", target="summarize"),
        EdgeConfig(source="summarize", target="merge"),
        EdgeConfig(source="merge", target="refine"),
      
        EdgeConfig(
            source="refine",
            target="refine",
            condition=Condition(key="summary_length", op=">", value=400),
        ),
        
    ]

    return GraphCreateRequest(nodes=nodes, edges=edges, start_node="split")


SAMPLE_GRAPH_ID: Optional[str] = None


def init_sample_graph():
    global SAMPLE_GRAPH_ID
    req = build_graph()
    SAMPLE_GRAPH_ID = create_graph(req)



# FastAPI App + Endpoints


app = FastAPI(title="Minimal Agent Workflow Engine")


@app.on_event("startup")
def startup_event():
    init_sample_graph()


@app.post("/graph/create", response_model=GraphCreateResponse)
async def create_graph_endpoint(req: GraphCreateRequest):
    graph_id = create_graph(req)
    return GraphCreateResponse(graph_id=graph_id)


@app.post("/graph/run", response_model=GraphRunResponse)
async def run_graph_endpoint(req: GraphRunRequest):
    run = run_graph(req.graph_id, req.initial_state)
    return GraphRunResponse(
        run_id=run.run_id,
        final_state=run.state,
        log=run.log,
    )


@app.get("/graph/state/{run_id}", response_model=GraphStateResponse)
async def graph_state_endpoint(run_id: str):
    run = get_run_state(run_id)
    return GraphStateResponse(
        run_id=run.run_id,
        graph_id=run.graph_id,
        status=run.status,
        current_node=run.current_node,
        state=run.state,
        log=run.log,
    )


@app.get("/graph/sample_id")
async def sample_id():
    if SAMPLE_GRAPH_ID is None:
        raise HTTPException(status_code=500, detail="Sample graph not initialized")
    return {"graph_id": SAMPLE_GRAPH_ID}
