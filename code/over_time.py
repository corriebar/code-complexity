"""
Functions to jump through the git history of a repo.
"""
from datetime import datetime
import pathlib
import subprocess
from typing import Callable, Dict, Optional, Sequence, Tuple, TypeVar, Union

import pandas as pd

from code.complexity_metrics import COMPLEXITY_METRICS, get_repo_complexities

try:
    from fastprogress import progress_bar
except ModuleNotFoundError:
    progress_bar = lambda x: None


PathLike = Union[str, pathlib.Path]
T = TypeVar("T")


def git_log(dp: PathLike) -> Tuple[str, ...]:
    """Returns a tuple of all commit hashes in the git history (newest first)."""
    output = subprocess.check_output(["git", "-C", str(dp), "log", '--format=format:"%H"'])
    output = output.strip().decode("ascii")
    output = output.replace('"', "")
    return tuple(output.split("\n"))


def git_commit_timestamps(dp: PathLike) -> Dict[str, datetime]:
    """Returns a tuple of all commit hashes in the git history (newest first)."""
    output = subprocess.check_output(["git", "-C", str(dp), "log", '--format=format:"%H|%ci"'])
    output = output.strip().decode("ascii")
    output = output.replace('"', "")
    result = {}
    for row in output.split("\n"):
        cid, ts = row.split("|")
        result[cid] = datetime.fromisoformat(ts)
    return result


def git_status(dp: PathLike) -> str:
    """Returns the git status message."""
    output = subprocess.check_output(["git", "-C", str(dp), "status"])
    output = output.strip().decode("ascii")
    return output


def git_current_branch(dp: PathLike) -> str:
    """Determines the name of the currently checked-out branch."""
    status = git_status(dp)
    return status.split("\n")[0].replace("On branch ", "")


def git_checkout(dp: PathLike, commit_or_branch: str):
    """Check out a specific branch or commit in the repository under `dp`."""
    output = subprocess.check_output(["git", "-C", str(dp), "checkout", commit_or_branch])
    output = output.strip().decode("ascii")
    return output



def eval_by_commit(
    dp: PathLike,
    func: Callable[[PathLike], T],
    commits: Sequence[str],
    *,
    raise_on_error: bool = True,
) -> Dict[str, Optional[T]]:
    """Apply `func` to the `dp` for each of the `commits` and return the results.
    
    Requires the repository at `dp` to be in a clean `git status` state.
    In the end, the current branch will be checked out again.

    Parameters
    ----------
    dp
        Path to a local git repository.
    func
        A callable to apply at each commit.
        It should take one parameter `dp` and return something.
    commits
        A sequence of commits to execute the function at.
    raise_on_error
        If ``True``, exceptions other than SyntaxErrors are raised.

    Returns
    -------
    results
        Maps commit IDs to return values of the provided callable,
        or ``None`` in case of syntax errors at the respective commit.
    """
    status = git_status(dp)
    if "working tree clean" not in status and "nothing added to commit but untracked" not in status:
        raise Exception(f"The git status of '{dp}' is unclean:\n\n{status}")
    branch = git_current_branch(dp)
    results = {}
    for commit in progress_bar(commits):
        try:
            git_checkout(dp, commit)
            results[commit] = func(dp)
        except SyntaxError:
            results[commit] = None
        except:
            print(f"Failed to apply function at commit {commit}")
            if raise_on_error:
                raise
    print(f"\nEvaluations completed. Checking out branch '{branch}'.")
    git_checkout(dp, branch)
    return results


def complexity_by_commit(dp: PathLike, commits: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """Convenience wrapper around ``eval_by_commit`` to determine mean code complexity metrics over time.

    Parameters
    ----------
    dp
        Path to a local git repository.
    commits
        Optional sequence of commits IDs to run for.
        Defaults to the entire git history of the repo.

    Returns
    -------
    df
        DataFrame indexed by `commit_id`,
        with `timespan` and mean `COMPLEXITY_METRICS` columns.
    """
    if not commits:
        commits = git_log(dp)

    results = eval_by_commit(
        dp=dp,
        func=lambda dp: get_repo_complexities(dp).set_index("repo")[COMPLEXITY_METRICS].mean(),
        commits=commits,
    )

    # Summarize in a DataFrame with None-results as NA rows
    results_notna = {k:v for k,v in results.items() if v is not None}
    df = pd.DataFrame.from_dict(results_notna, orient="index")
    df.index.name = "commit_id"
    # Re-insert rows with None-results
    for k, v in results.items():
        if v is None:
            df.loc[k] = pd.NA

    # Determine commit timestamps
    timestamps = git_commit_timestamps(dp)
    df["timestamp"] = [timestamps[row.Index] for row in df.itertuples()]
    return df.sort_values("timestamp")
