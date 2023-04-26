import datetime
from pathlib import Path

from flake8_functions.function_length import get_function_start_row, get_function_last_row
from cognitive_complexity.api import get_cognitive_complexity
from flake8_expression_complexity.utils.complexity import get_expression_complexity

from flake8_functions.function_arguments_amount import get_arguments_amount_for
from flake8_functions.function_returns_amount import get_returns_amount_for

from code.parse_code import (
    iterate_over_expressions,
    get_function_definitions,
    parse_file,
    get_all_python_files,
)

import pandas as pd

COMPLEXITY_METRICS = [
    "func_length",
    "cognitive_complexity",
    "sum_expression_complexity",
    "max_expression_complexity",
    "num_arguments",
    "num_returns",
    "num_module_expressions",
    "module_complexity",
]
"""
Only the metrics columns of the complexity analysis.

This can be used e.g. to summarize the DataFrame.
"""

COMPLEXITY_COLUMNS = [
    "repo",
    "file",
    "function_name",
    "func_lineno",
    "extract_date",
    *COMPLEXITY_METRICS,
]
"""All columns to expect in a complexity analysis DataFrame."""

COLUMN_TYPES = {
    "repo": str,
    "file": str,
    "function_name": str,
    "func_lineno": "float64",
    "func_length": "float64",
    "cognitive_complexity": "float64",
    "sum_expression_complexity": "float64",
    "max_expression_complexity": "float64",
    "num_arguments": "float64",
    "num_returns": "float64",
    "num_module_expressions": "float64",
    "module_complexity": "float64",
}


def get_function_length(funcdef):
    function_start_row = get_function_start_row(funcdef)
    function_last_row = get_function_last_row(funcdef)
    return function_last_row - function_start_row + 1


def get_complexity_per_function(funcdef):
    expression_complexities = [
        get_expression_complexity(expr) for expr in iterate_over_expressions(funcdef)
    ]
    return {
        "function_name": funcdef.name,
        "func_lineno": funcdef.lineno,
        "func_length": get_function_length(funcdef),
        "cognitive_complexity": get_cognitive_complexity(funcdef),
        "sum_expression_complexity": sum(expression_complexities),
        "max_expression_complexity": max(expression_complexities),
        "num_arguments": get_arguments_amount_for(funcdef),
        "num_returns": get_returns_amount_for(funcdef),
    }


def get_module_complexities(module):
    expressions_outside_functions = [exp for exp in iterate_over_expressions(module)]
    expression_complexities = [
        get_expression_complexity(expr) for expr in expressions_outside_functions
    ]
    num_expressions = len(expressions_outside_functions)
    return {
        "num_module_expressions": num_expressions,
        "module_complexity": sum(expression_complexities),
    }


def get_module_function_complexities(module):
    complexities = []
    funcdefs = get_function_definitions(module)

    for funcdef in funcdefs:
        comp_dict = get_complexity_per_function(funcdef)
        complexities.append(comp_dict)

    return complexities


def get_file_complexities(repo_path: Path, filepath: Path):
    module = parse_file(filepath)

    function_complexities = get_module_function_complexities(module)

    module_complexities = get_module_complexities(module)

    rel_path = str(filepath.relative_to(repo_path))
    module_function_complexities = [
        {**d, **module_complexities, "file": rel_path}
        for d in function_complexities
    ]
    return module_function_complexities


def get_repo_complexities(repo_path):
    repo_path = Path(repo_path)
    repo_name = repo_path.name

    python_files = get_all_python_files(repo_path, repo_name)
    complexities = []
    for file_path in python_files:
        module_function_complexities = get_file_complexities(repo_path, file_path)

        complexities.extend(module_function_complexities)

    df = pd.DataFrame(complexities, columns=COMPLEXITY_COLUMNS)
    df["repo"] = repo_name
    df = add_extract_date(df)
    return df[COMPLEXITY_COLUMNS].sort_values(
        by=["cognitive_complexity", "func_length"], ascending=False
    )


def add_extract_date(df):
    today = datetime.datetime.today()
    d = df.copy()
    d["extract_date"] = str(today.date())
    return d


def compare_old_new(old_df, new_df):
    sort_cols = ["repo", "file", "function_name"]
    compare_cols = [
        *sort_cols,
        "func_lineno",
        "func_length",
        "cognitive_complexity",
        "sum_expression_complexity",
        "max_expression_complexity",
        "num_arguments",
        "num_returns",
        "num_module_expressions",
        "module_complexity",
    ]
    old = old_df[compare_cols].sort_values(by=sort_cols).reset_index(drop=True).astype(COLUMN_TYPES)
    new = new_df[compare_cols].sort_values(by=sort_cols).reset_index(drop=True).astype(COLUMN_TYPES)
    is_equal = old.equals(new)
    return is_equal


def get_latest_data(old_data):
    return old_data.query("extract_date == extract_date.max()")
