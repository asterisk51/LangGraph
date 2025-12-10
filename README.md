# AI Workflow Orchestration Engine
### Tredence – AI Engineering Assignment
## Overview

This project implements a graph-based workflow orchestration engine for building and executing stateful, multi-step AI pipelines.
The engine allows users to define workflows as directed graphs consisting of nodes (tools) and edges (transitions), supporting conditional branching, looping, shared state management, and execution logging.

The system is implemented using Python and FastAPI, and exposes APIs for creating workflows, executing them, and retrieving execution state.

A sample workflow demonstrating multi-step text summarization with refinement is included.

## Key Features
### Graph-Driven Execution

Workflows are represented as graphs where each node corresponds to a tool and edges define transitions. This supports sequential flows, conditional paths, and loops.

### Shared Stateful Engine

Each tool operates on a shared state dictionary. Tools may read, modify, or add information to the state, enabling incremental computation across workflow steps.

### Conditional Branching

Edges may include conditions (e.g., summary_length > 400). At runtime, transitions are selected based on evaluated conditions.

### Loop Support

Loops are implemented by routing edges back to previously executed nodes when conditions are met.
For example, the refinement step in the sample workflow repeats until the summary meets a target length.

### Execution Trace and State Introspection

Each run produces a step-by-step execution log capturing:

* Node executed

* Tool applied

* Snapshot of state after the step

Users can retrieve current or final state using the run identifier.

### FastAPI Interface

The system exposes REST APIs for:

* Creating workflows

* Triggering execution

* Inspecting run state

Interactive API documentation is available via Swagger UI.

## Architecture Summary

* Tool Registry: Tools are registered dynamically using decorators.

* Graph Definition: Nodes, edges, and starting node form a workflow definition.

* Execution Engine: Runs a graph from its starting node until no valid transition remains.

* State Manager: Maintains and updates state across nodes.

* Run Manager: Stores execution history and run metadata.

## Installation
```pip install fastapi uvicorn pydantic``

## Running the Server
```uvicorn app.main:app --reload``


### API documentation appears at:

http://localhost:8000/docs

## API Endpoints
### Create a Graph

`POST /graph/create`
Defines a new workflow by specifying nodes, edges, and the start node.

### Run a Graph

`POST /graph/run`
Executes a workflow with an initial state and returns the run ID, final state, and execution log.

### Get Run State

`GET /graph/state/{run_id}`
Retrieves execution status, state, and logs of a specific workflow run.

### Sample Workflow

`GET /graph/sample_id`
Returns a pre-configured summarization workflow included with the engine.

## Sample Workflow: Summarization with Refinement

The project includes a complete example that performs:

1. Text splitting

2. Chunk-level summarization

3. Merging partial summaries

4. Refinement iterations until a target length is achieved

### Nodes
| Node | Tool | Description |
| --- | --- |
| split | split_text | Splits text into fixed-size chunks |
| summarize | summarize_chunks | Summarizes each chunk |
| merge | merge_summaries | Merges partial summaries |
| refine | refine_summary | Shortens summary iteratively |
### Loop Condition

The workflow loops on the `refine` node while:

`summary_length > 400`


This demonstrates the engine’s ability to handle branching and looping with state-based conditions.

## Design Highlights

* Tools are modular, stateless functions that read and modify a global state dictionary.

* Workflows allow flexible control flow modeling through graph edges.

* Execution snapshots enable debugging, monitoring, and reproducibility.

* FastAPI provides a clean API surface for programmatic or manual testing.

## Future Enhancements

If extended beyond assignment scope, improvements could include:

* Persistent storage (SQLite/Postgres) for graphs and runs

* Asynchronous or distributed execution

* Richer condition expressions

* User-defined state schemas

* Web interface for visual workflow construction

* LLM-powered tools for more advanced workflows

## Purpose

This implementation was developed as part of Tredence’s AI Engineering assignment to demonstrate skills in designing workflow engines, managing state, handling conditional logic, and exposing functionalities via APIs.