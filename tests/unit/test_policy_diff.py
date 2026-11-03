from __future__ import annotations

from cleartrace_policy_watch.diff import diff_clause_trees


def test_formatting_only_change_not_substantive() -> None:
    before_norm = {"1.1": "requires an algorithmic impact assessment before production"}
    after_norm = {"1.1": "requires an algorithmic impact assessment before production"}
    raw_before = {"1.1": "Requires an algorithmic impact assessment before production."}
    raw_after = {"1.1": "Requires   an algorithmic impact assessment before production."}
    result = diff_clause_trees(before_norm, after_norm, raw_before=raw_before, raw_after=raw_after)
    assert result.substantive_count == 0
    assert result.formatting_only_count == 1
