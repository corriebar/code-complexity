import ast
import itertools
from pathlib import Path
from typing import Callable, Iterable, List, Tuple


_IGNORE_DIRS = {
    "notebooks",
    ".ipynb_checkpoints",
}


def parse_file(filepath):
    with open(filepath) as f:
        file_parsed = ast.parse(f.read())
    return file_parsed


def get_all_python_files(repo_path, repo) -> List[Path]:
    python_files = []
    for fp_py in Path(repo_path).glob("**/*.py"):
        if fp_py.is_dir() or any(d in str(fp_py) for d in _IGNORE_DIRS):
            continue
        python_files.append(fp_py)
    return python_files


def get_function_definitions(module):
    funcdefs = [
        n for n in ast.walk(module) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return funcdefs


def iterate_over_expressions(node: ast.AST) -> Iterable[ast.AST]:
    """Ignoring function definitions."""
    additionals_subnodes_info: List[Tuple[Tuple, Callable]] = [
        ((ast.If, ast.While), lambda n: [n.test]),
        ((ast.For,), lambda n: [n.iter]),
        ((ast.AsyncFor,), lambda n: [n.iter]),
        ((ast.With, ast.AsyncWith), lambda n: [s.context_expr for s in n.items]),
    ]
    nodes_with_subnodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.Module,
        ast.ClassDef,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        ast.While,
    )
    for bases, subnodes_getter in additionals_subnodes_info:
        if isinstance(node, bases):
            yield from subnodes_getter(node)
    nodes_to_iter = (
        _get_try_node_children(node) if isinstance(node, ast.Try) else getattr(node, "body", [])
    )
    for child_node in nodes_to_iter:
        if isinstance(child_node, nodes_with_subnodes):
            if not isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from iterate_over_expressions(child_node)
        else:
            yield child_node


def _get_try_node_children(try_node: ast.Try):
    return itertools.chain(try_node.body, try_node.finalbody, *[n.body for n in try_node.handlers])
