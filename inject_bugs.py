import ast
import json
import multiprocessing
import random
from pathlib import Path
import astor
import networkx as nx
import argparse

class CallGraphVisitor(ast.NodeVisitor):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.current_func = "global"

    def visit_FunctionDef(self, node):
        prev_func = self.current_func
        self.current_func = node.name
        self.graph.add_node(node.name, type="function", lineno=node.lineno)
        self.generic_visit(node)
        self.current_func = prev_func

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            called_func = node.func.id
            self.graph.add_edge(self.current_func, called_func, type="calls")
        self.generic_visit(node)


class BugInjector(ast.NodeTransformer):
    def __init__(self, mutation_rate: float = 1.0):
        self.mutation_rate = mutation_rate
        self.mutated = False
        self.bug_type = None

    def visit_Compare(self, node):
        if not self.mutated and random.random() <= self.mutation_rate:
            op_map = {
                ast.Lt: ast.LtE(),
                ast.LtE: ast.Lt(),
                ast.Gt: ast.GtE(),
                ast.GtE: ast.Gt(),
                ast.Eq: ast.NotEq(),
                ast.NotEq: ast.Eq(),
            }
            if type(node.ops[0]) in op_map:
                node.ops[0] = op_map[type(node.ops[0])]
                self.mutated = True
                self.bug_type = "Boundary Error or Logical Error"
        return self.generic_visit(node)

    def visit_BinOp(self, node):
        if not self.mutated and random.random() <= self.mutation_rate:
            op_map = {
                ast.Add: ast.Sub(),
                ast.Sub: ast.Add(),
                ast.Mult: ast.Div(),
                ast.Div: ast.Mult(),
            }
            if type(node.op) in op_map:
                node.op = op_map[type(node.op)]
                self.mutated = True
                self.bug_type = "Arithmetic Error"
        return self.generic_visit(node) 

    def visit_If(self, node):
        ##control flow inversion which negates if condition
        if not self.mutated and random.random() <=self.mutation_rate:
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            self.mutated = True #Wrap test in an ast.Not() unary operation
            self.bug_type = "Control Flow Inversion error"
        return self.generic_visit(node)    

    def visit_Return(self, node):
        ##return value mutation (forces null/zero return)
        if not self.mutated and random.random() <= self.mutation_rate and node.value is not None:
            ## replace actual return value with constant 0 or none
            node.value = ast.Constant(value=0)
            self.mutated = True
            self.bug_type = "Return Value Mutation Error"
        return self.generic_visit(node)    

def process_file(file_path: Path):
    try:
        clean_code = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(clean_code)

        visitor = CallGraphVisitor()
        visitor.visit(tree)
        graph_data = nx.node_link_data(visitor.graph)

        injector = BugInjector(mutation_rate=1.0)
        mutated_tree = injector.visit(tree)

        if injector.mutated:
            mutated_code = astor.to_source(mutated_tree)
            return {
                "file_path": str(file_path),
                "instruction": f"Identify and fix {injector.bug_type} in this code",
                "input_code": mutated_code,
                "dependency_graph": graph_data,
                "output_fix": clean_code,
            }
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return None


def generate_curriculum(target_path, output_file, num_workers=4):
    p = Path(target_path)
    if p.is_file() and p.suffix == ".py":
        target_files = [p]
    elif p.is_dir():
        target_files = [f for f in p.rglob("*.py") if not f.name.startswith("test_")]
    else:
        print(f"Error: Invalid target path '{target_path}'")
        return

    print(f"Found {len(target_files)} target Python file(s) for mutation...")

    with multiprocessing.Pool(num_workers) as pool:
        results = pool.map(process_file, target_files)

    curriculum = [r for r in results if r is not None]

    with open(output_file, "w", encoding="utf-8") as f:
        for item in curriculum:
            f.write(json.dumps(item) + "\n")

    print(f"Curriculum generation complete. {len(curriculum)} synthetic bug-fix pairs created.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", "-t", required=True, help="Target file or folder")
    parser.add_argument("--output", "-o", default="./gemma_training_curriculum.jsonl")
    parser.add_argument("--workers", "-w", type=int, default=4)

    args = parser.parse_args()
    generate_curriculum(args.target, args.output, num_workers=args.workers)