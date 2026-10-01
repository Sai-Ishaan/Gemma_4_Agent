### Supporting ADK Skill Manifest
In order to perform custom graph processing, (e.g; running NetworkX shortest-path algorithms locally), wrap your Python Logic in an ADK Skill:

```yaml
---
name: graph_navigation
description: "Executes custom graph traversal and vector math using local NumPy and NetworkX libraries inside the sandbox."
```
-----------

### Graph Navigation Skill
This skill provides python utilities for graph traversal over NetworkX AST files:

- `scripts/path_finder.py`: Computes shortest dependency path between two AST symbol nodes.
- `resources/graph_schema.md`: Reference documentation for node attribute keys in the serialized NetworkX JSONs.