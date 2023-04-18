from string import ascii_uppercase
from typing import List

from gspread_dataframe import get_as_dataframe
from gspread_formatting import get_conditional_format_rules
from gspread_formatting.dataframe import format_with_dataframe, set_frozen
from gspread_formatting.models import Color
from gspread_formatting.conditionals import (
    ConditionalFormatRule,
    GradientRule,
    GridRange,
    InterpolationPoint,
)

from gspread_dataframe import get_as_dataframe, set_with_dataframe


import pandas as pd

from code.complexity_metrics import COLUMN_TYPES, compare_old_new, get_latest_data


COLUMN_GRADIENTS = {
    "func_length": [0, 50, 80],
    "cognitive_complexity": [0, 7, 10],
    "sum_expression_complexity": [0, 50, 80],
    "max_expression_complexity": [0, 6, 9],
    "num_arguments": [0, 4, 7],
    "num_returns": [0, 3, 7],
}

GREEN = Color(0.34117648, 0.73333335, 0.5411765)
YELLOW = Color(0.9843137, 0.7372549, 0.015686275)
RED = Color(1, 0.42745098, 0.003921569)


def get_old_data(sheet, repo):
    types = {**COLUMN_TYPES, "extract_date": str}
    wksh = sheet.worksheet(repo)
    old_data = get_as_dataframe(wksh)
    old_df = old_data.dropna(axis=1, how="all")  # drop empty columns
    return old_df.dropna(axis=0, how="all").astype(types)


def return_data_to_write(sheet, repo, new_df):
    old_df = get_old_data(sheet, repo)
    latest = get_latest_data(old_df)
    if not compare_old_new(latest, new_df):
        print(f"Changes have been made in {repo}!")
        df = pd.concat([new_df, old_df], ignore_index=True)
    else:
        df = old_df
    return df


def get_cell_ranges(worksheet, cell_ranges: str | List):
    ranges = []
    if isinstance(cell_ranges, str):
        cell_ranges = [cell_ranges]
    for cells in cell_ranges:
        grid_range = GridRange.from_a1_range(cells, worksheet)
        ranges.append(grid_range)
    return ranges


def get_conditional_format_rule(worksheet, cell_ranges: str | List, gradient_points: List[int]):
    minpoint, midpoint, maxpoint = gradient_points

    ranges = get_cell_ranges(worksheet, cell_ranges)
    rule = ConditionalFormatRule(
        ranges=ranges,
        gradientRule=GradientRule(
            minpoint=InterpolationPoint(color=GREEN, type="NUMBER", value=str(minpoint)),
            midpoint=InterpolationPoint(color=YELLOW, type="NUMBER", value=str(midpoint)),
            maxpoint=InterpolationPoint(color=RED, type="NUMBER", value=str(maxpoint)),
        ),
    )
    return rule


def map_colname_to_range(df, colname):
    col_index = list(df.columns).index(colname)
    if col_index > 26:
        print("not yet supported")
    col_letter = ascii_uppercase[col_index]
    return f"{col_letter}:{col_letter}"


def set_conditional_rules(df, rules, worksheet):
    for col_name, gradient_points in COLUMN_GRADIENTS.items():
        cell_range = map_colname_to_range(df, col_name)
        rule = get_conditional_format_rule(worksheet, cell_range, gradient_points)
        rules.append(rule)
    rules.save()


def apply_formatting(worksheet, df):
    set_with_dataframe(worksheet, df)
    format_with_dataframe(worksheet, df, include_column_header=True)
    set_frozen(worksheet, rows=1)

    rules = get_conditional_format_rules(worksheet)
    set_conditional_rules(df, rules, worksheet)
