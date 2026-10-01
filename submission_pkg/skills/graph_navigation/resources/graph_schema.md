### Multi-Dimensional Codebase Graph Schema
This repository is represented as a combined DAG (Directed Acyclic Graph) containing three distinct dimensional layers. While constructing your `pedagological_trace`, you must link nodes using the following relation types:

#### A) Static AST Layer (Structural)
 - **Node Type:** `ast_symbol` (Functions, Classes, Methods)
 - **Edges:**
     -> `CALLS`: node A invokes B
     -> `DEPENDS_ON`: node A imports or inherits from B.

#### B) Dynamic DFG Layer (Runtime/Data flow)
 - **Node Type:** 'config_state', 'injected_dependency'

 - **Edges:**
    -> `INJECTS_INTO`: A runtime state or dependency container feeds into Node B.
    -> `Configures`: A yaml/JSON/Env node defines the parameters of Node B.

#### C) Temporal Git Layer (Lineage)
   - **Node Type:** `git commit` (Hash, Author, Date, Message)
   - **Edges:**
    -> **MODIFIED_BY:** Node A was altered by Git Commit B. Useful for regression tracking, finding the intent behind breaking change.