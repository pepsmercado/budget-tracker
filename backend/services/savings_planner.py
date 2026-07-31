"""Savings Planner engine.

Pure, shared logic that both backends use. It guarantees the invariant:

    Savings Balance = Reserves + Goals + Unallocated

Unallocated is never stored — it is derived from the live account balance and
the stored allocations:

    Unallocated = live_balance - sum(reserve.allocated) - sum(goal.allocated)

All functions here mutate the passed-in reserve/goal model objects in place and
return a list of activity-event dicts for the caller to persist.
"""

from typing import Optional


def unallocated(live_balance: float, reserves: list, goals: list) -> float:
    return round(live_balance - sum(r.allocated for r in reserves) - sum(g.allocated for g in goals), 2)


def _fmt(amount: float) -> str:
    return f"{amount:,.2f}"


def _deduction_order(goals: list, reserves: list) -> list:
    """Order buckets are reduced on a savings balance decrease.

    Lowest-priority goal first (highest position), then reserves by priority
    (highest position first) regardless of floor. Floored reserves stop at
    their floor.
    """
    goals_sorted = sorted(goals, key=lambda g: g.position, reverse=True)
    reserves_sorted = sorted(reserves, key=lambda r: r.position, reverse=True)
    return [("goal", g) for g in goals_sorted] + [("reserve", r) for r in reserves_sorted]


def completed_goals(goals: list) -> list:
    """Goals that have reached their target and should move to Reserves."""
    return [
        g for g in goals
        if g.target is not None and g.target > 0
        and round(g.allocated, 2) >= round(g.target, 2)
    ]


def _replenishment_order(goals: list) -> list:
    """Highest-priority goal first (lowest position)."""
    return sorted(goals, key=lambda g: g.position)


def reconcile(live_balance: float, reserves: list, goals: list) -> tuple[list, list, list, bool]:
    """Bring buckets in line with a changed savings balance.

    - Balance increased: nothing changes; Unallocated grows by definition.
    - Balance decreased: deduct from Unallocated first (derived), then buckets
      in priority order until the equation holds.

    Returns (reserves, goals, events, underfunded).
    """
    events: list[dict] = []
    shortfall = round(-unallocated(live_balance, reserves, goals), 2)
    if shortfall <= 0:
        return reserves, goals, events, False

    underfunded = False
    for kind, bucket in _deduction_order(goals, reserves):
        if shortfall <= 0:
            break
        max_take = bucket.allocated
        if kind == "reserve" and bucket.floor is not None:
            max_take = round(max(0.0, bucket.allocated - bucket.floor), 2)
        take = round(min(max_take, shortfall), 2)
        if take > 0:
            bucket.allocated = round(bucket.allocated - take, 2)
            shortfall = round(shortfall - take, 2)
            events.append({
                "type": "Planner Recalculated",
                "amount": take,
                "description": f"Savings balance decreased; pulled {_fmt(take)} from {bucket.name}",
            })

    if shortfall > 0:
        underfunded = True
        events.append({
            "type": "Planner Recalculated",
            "amount": shortfall,
            "description": f"Savings balance decrease of {_fmt(shortfall)} could not be fully covered by reserves and goals.",
        })

    return reserves, goals, events, underfunded


def replenish_floor(reserve, reserves: list, goals: list, live_balance: float) -> tuple[list, list, list]:
    """Attempt to bring a floored reserve up to its floor.

    Pulls from Unallocated first, then lowest-priority goals in ascending
    priority. Returns (reserves, goals, events).
    """
    events: list[dict] = []
    if reserve.floor is None:
        return reserves, goals, events
    shortfall = round(reserve.floor - reserve.allocated, 2)
    if shortfall <= 0:
        return reserves, goals, events

    avail = round(unallocated(live_balance, reserves, goals), 2)
    if avail > 0:
        take = round(min(shortfall, avail), 2)
        reserve.allocated = round(reserve.allocated + take, 2)
        shortfall = round(shortfall - take, 2)
        events.append({
            "type": "Reserve Replenished",
            "amount": take,
            "description": f"{reserve.name} replenished {_fmt(take)} from Unallocated",
        })

    for goal in _replenishment_order(goals):
        if shortfall <= 0:
            break
        take = round(min(goal.allocated, shortfall), 2)
        if take > 0:
            goal.allocated = round(goal.allocated - take, 2)
            reserve.allocated = round(reserve.allocated + take, 2)
            shortfall = round(shortfall - take, 2)
            events.append({
                "type": "Reserve Replenished",
                "amount": take,
                "description": f"{reserve.name} replenished {_fmt(take)} from {goal.name}",
            })

    if shortfall > 0:
        events.append({
            "type": "Planner Recalculated",
            "amount": shortfall,
            "description": f"Insufficient funds to fully replenish {reserve.name}; resolve manually.",
        })

    return reserves, goals, events


def _find_bucket(reserves: list, goals: list, bucket_id: str):
    for r in reserves:
        if r.id == bucket_id:
            return "reserve", r
    for g in goals:
        if g.id == bucket_id:
            return "goal", g
    return None, None


def _max_available(kind, bucket, live_balance: float, reserves: list, goals: list) -> float:
    if bucket is None:
        return unallocated(live_balance, reserves, goals)
    if kind == "reserve" and bucket.floor is not None:
        return round(max(0.0, bucket.allocated - bucket.floor), 2)
    return round(bucket.allocated, 2)


def move_money(live_balance: float, reserves: list, goals: list,
               from_bucket_id: str, to_bucket_id: str, amount: float) -> tuple[list, list, list, Optional[str]]:
    """Move money between buckets (or Unallocated).

    Overfunding is capped: excess spills back to Unallocated. Floored reserves
    cannot be drained below their floor.

    Returns (reserves, goals, events, error).
    """
    if from_bucket_id == to_bucket_id:
        return reserves, goals, [], "Cannot move money to the same bucket"

    src_kind, src = _find_bucket(reserves, goals, from_bucket_id)
    dst_kind, dst = _find_bucket(reserves, goals, to_bucket_id)

    if from_bucket_id != "unallocated" and src is None:
        return reserves, goals, [], "Source bucket not found"
    if to_bucket_id != "unallocated" and dst is None:
        return reserves, goals, [], "Destination bucket not found"

    src_name = "Unallocated" if src is None else src.name
    dst_name = "Unallocated" if dst is None else dst.name

    available = _max_available(src_kind, src, live_balance, reserves, goals)
    if round(available, 2) < round(amount, 2):
        return reserves, goals, [], f"Insufficient funds in {src_name}"

    if src is not None:
        src.allocated = round(src.allocated - amount, 2)

    events: list[dict] = []
    actual_to = amount
    if dst is not None:
        if dst_kind == "goal":
            room = round(max(0.0, dst.target - dst.allocated), 2)
            actual_to = round(min(amount, room), 2)
            spill = round(amount - actual_to, 2)
            dst.allocated = round(dst.allocated + actual_to, 2)
            if spill > 0:
                events.append({
                    "type": "Planner Recalculated",
                    "amount": spill,
                    "description": f"{_fmt(spill)} spilled to Unallocated ({dst.name} target reached)",
                })
        else:
            dst.allocated = round(dst.allocated + amount, 2)

    events.insert(0, {
        "type": "Moved Funds",
        "amount": amount,
        "description": f"Moved {_fmt(amount)} from {src_name} to {dst_name}",
    })

    if dst_kind == "goal" and round(dst.allocated, 2) >= round(dst.target, 2):
        events.append({
            "type": "Goal Completed",
            "amount": dst.allocated,
            "description": f"Goal '{dst.name}' reached its target",
        })

    return reserves, goals, events, None
