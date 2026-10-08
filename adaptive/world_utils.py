"""Utility functions for adaptive worlds. Split from worlds.py for the
200-line limit. Provides c1_blocks, condition_at, and the common
block-integrity assertion used by all five generators.
"""
from __future__ import annotations
from .worlds import AdaptiveWorld, load_policy

__all__ = ["c1_blocks", "condition_at"]

_P = load_policy()
_L = int(_P["stream"]["block_length"])
_KEY = str(_P["stream"]["key"])
_TARGET = str(_P["stream"]["target"])


def c1_blocks(world: AdaptiveWorld) -> list[tuple[int, int]]:
    """First and last round of each c1 block, in order."""
    blocks, start = [], None
    for o in world.observations:
        key = list(o["conditions"].keys())[0]
        is_t = o["conditions"][key] == _TARGET
        if is_t and start is None:
            start = o["seq"]
        elif not is_t and start is not None:
            blocks.append((start, o["seq"] - 1))
            start = None
    if start is not None:
        blocks.append((start, world.observations[-1]["seq"]))
    return blocks


def condition_at(world: AdaptiveWorld, seq: int) -> dict:
    """The target condition written in the vocabulary in force at seq."""
    if world.planted.get("world") != "V":
        return dict(world.condition)
    renames = world.planted.get("renames", [])
    key_names = world.planted.get("key_names", [_KEY])
    ki = 0
    for r in renames:
        if seq >= r:
            ki = renames.index(r) + 1
        else:
            break
    return {key_names[ki]: _TARGET}


def assert_block_integrity(world: AdaptiveWorld) -> None:
    """Common assert: no vocab event/declaration strictly inside a c1 block;
    stream starts with c1 and ends with c2."""
    blocks = c1_blocks(world)
    assert blocks, "no c1 blocks found"
    assert blocks[0][0] == 0, "stream must start with c1"
    last_obs = world.observations[-1]
    last_key = list(last_obs["conditions"].keys())[0]
    assert last_obs["conditions"][last_key] != _TARGET, \
        "stream must end with c2 (last block must be c2)"
    for a, b in blocks:
        for d in world.declarations:
            assert not (a < d["seq"] <= b), \
                f"declaration at seq {d['seq']} inside c1 block [{a},{b}]"
        for e in world.vocabulary_events:
            assert not (a < e["seq"] <= b), \
                f"vocab event at seq {e['seq']} inside c1 block [{a},{b}]"
