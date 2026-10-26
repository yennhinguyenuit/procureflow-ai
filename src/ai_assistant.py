"""Offline summaries retained for existing reports and the Streamlit interface.

Interactive local-model planning and grounded chat live in src.local_agent.
This module never imports a cloud SDK or contacts any network service.
"""
from __future__ import annotations

import math
import re
from typing import Any

from src.validation import SKU_PATTERN

FALLBACK_SOURCE = 'RULE_BASED_FALLBACK'
_APPROVAL_NOTICE = (
    'Draft recommendations require human approval and are not supplier orders. '
    'Purchase quantities are calculated by the deterministic policy, never by AI.'
)


def _nonnegative_int(value: Any) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool)
            and 0 <= value <= 1_000_000_000_000_000_000)


def fallback_summary(rows: list[dict[str, Any]]) -> str:
    """Explain trusted deterministic results without network access or writes."""
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get('sku'), str)
        or re.fullmatch(SKU_PATTERN, row['sku']) is None
        or not _nonnegative_int(row.get('quantity'))
        or not _nonnegative_int(row.get('estimated_cost_vnd'))
        for row in rows
    ):
        return ('Rule-based summary: source data needs validation before review. '
                + _APPROVAL_NOTICE)
    needs = [row for row in rows if row['quantity'] > 0]
    if needs:
        total = sum(row['estimated_cost_vnd'] for row in needs)
        skus = ', '.join(row['sku'] for row in needs)
        overview = (f'Rule-based summary: {len(needs)} SKU(s) require review ({skus}). '
                    f'Estimated total value: {total:,} VND. '
                    'Inventory shortages may disrupt operations if deliveries arrive late.')
    else:
        overview = 'No replenishment is currently recommended by the deterministic policy.'
    changes = [
        f"{row['sku']} {row['demand_change_pct']:+.1f}%"
        for row in rows
        if isinstance(row.get('demand_change_pct'), (int, float))
        and not isinstance(row['demand_change_pct'], bool)
        and -100 <= row['demand_change_pct'] <= 1_000_000_000
        and math.isfinite(row['demand_change_pct'])
    ]
    demand = (
        'Historical demand comparison versus the previous equal-length window: '
        + '; '.join(changes) + '. This is a descriptive change, not a demand forecast.'
        if changes else
        'An aggregate demand average alone does not establish demand fluctuations or '
        'seasonality. Check the demand history before changing assumptions.'
    )
    quality_count = sum(row.get('risk') == 'Data Quality Issue' for row in rows)
    quality_note = (
        f' Data quality issues affect {quality_count} SKU(s); review source data and '
        'supplier assignments before replenishment.' if quality_count else ''
    )
    return (
        overview + quality_note + '\n\nDemand review: ' + demand + '\n\n'
        'Review checklist: verify physical stock and reservations; confirm pending '
        'deliveries and supplier lead times; review unusual demand and pack sizes.\n\n'
        + _APPROVAL_NOTICE
    )


def summarize(rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Return an English deterministic summary; configuration cannot enable cloud calls."""
    return fallback_summary(rows), FALLBACK_SOURCE
