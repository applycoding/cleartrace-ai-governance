"""Policy change watcher: snapshots, diff, steward gate, impact sets."""

from cleartrace_policy_watch.diff import ClauseChange, DiffResult, diff_clause_trees
from cleartrace_policy_watch.normalizer import normalize_clause_text
from cleartrace_policy_watch.service import PolicyWatcherService

__all__ = [
    "ClauseChange",
    "DiffResult",
    "PolicyWatcherService",
    "diff_clause_trees",
    "normalize_clause_text",
]
