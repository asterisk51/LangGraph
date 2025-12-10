#  AI Workflow Orchestration Engine
Tredence – AI Engineering Coding Assignment

This project implements a minimal yet extensible workflow orchestration engine using FastAPI, Python, and a graph-based execution model.
It satisfies all requirements of the assignment:

Define nodes (tools)

Connect them using edges with conditional branching

Maintain a shared state dictionary

Support looping until a condition is satisfied

Expose APIs for:

Creating a workflow (graph/create)

Running a workflow (graph/run)

Checking workflow state (graph/state/{run_id})

Provide a complete sample workflow (Summarization + Refinement) as required.

##  Features
-> Graph-based workflow execution

Each node is a "tool" operating on a shared state dict.

Edges define transitions between nodes.

Optional conditions allow branching and loops.

-> Tool Registry

Tools are functions registered with decorators via @register_tool.
New tools can be added easily without modifying the engine.

-> State Tracking + Logging

Every step logs:

Node name

Tool executed

Snapshot of the state

Accessible via graph/state/{run_id}.

-> Built-in Sample Workflow

A fully functional summarization pipeline:

split_text — Split input into chunks

summarize_chunks — Summarize each chunk

merge_summaries — Combine partial summaries

refine_summary — Shorten iteratively

Loop until summary_length <= 400

Automatically registered at startup.


##  Running the Server

Install dependencies:

pip install fastapi uvicorn pydantic


Start the server:

uvicorn app.main:app --reload


API docs:

👉 http://127.0.0.1:8000/docs

##  API Endpoints
### 1. Create a Workflow

POST /graph/create

Request structure:

{
  "nodes": [...],
  "edges": [...],
  "start_node": "split"
}


Returns:

{ "graph_id": "<uuid>" }

### 2️. Run a Workflow

POST /graph/run

Example:

{
  "graph_id": "<your-graph-id>",
  "initial_state": {
    "text": "Your long document here..."
  }
}


Returns:

run_id

final_state

log

### 3️. Check Workflow State

GET /graph/state/{run_id}

Returns:

Status (pending/running/completed/failed)

Current node

State dict

Execution log

### 4️. Get Sample Workflow ID

A pre-configured summarization workflow is created at startup.

Endpoint:

GET /graph/sample_id

Example response:

{ "graph_id": "6c7f...." }


Use this ID directly for testing.

##  Tool Registry

Tools are registered using:

@register_tool("tool_name")
def function(state, config):
    ...


This makes adding new tools extremely simple.

##  Design Choices & Possible Enhancements
-> Current Design Strengths

Fully modular tool system

Clean graph execution logic

Supports multi-step workflows with branching

Logging & step-by-step state replay

FastAPI makes APIs self-documented

-> If more time was available:

Add persistence (SQLite/Postgres) for graphs & runs

Add async execution & background processing

Stream logs via WebSockets

Integrate actual LLM-based summarization tools

Add schema validation for the state

##  Example: Running the Sample Workflow

Start server

Call:

GET /graph/sample_id


Use returned graph_id in:

POST /graph/run


Body:

{
  "graph_id": "<sample-id>",
  "initial_state": {
    "text": "Paste long text here for summarization..."
  }
}


Check state:

GET /graph/state/<run-id>