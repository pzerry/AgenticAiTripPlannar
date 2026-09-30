"""Bounded retrieval and explicit tracking of memory-supplied trip defaults."""

from dataclasses import dataclass
import json
from uuid import UUID

from psycopg import AsyncConnection

from Backend.Memory.models import ALLOWED_VALUES
from Backend.Memory.semantic_memory import SemanticMemoryRepository
from Backend.Schemas.travel_schema import TravelPlan


@dataclass(frozen=True)
class RetrievedMemory:
    preferences: dict[str, str]
    selected_ids: tuple[str, ...]


async def retrieve_preferences(conn: AsyncConnection, *, user_id: UUID,
                               max_characters: int = 2048) -> RetrievedMemory:
    """Exact lookup is bounded by the three supported keys; no embedding call."""
    if max_characters < 2:
        raise ValueError("Memory context budget must fit an empty JSON object")
    rows = await SemanticMemoryRepository().get_all(conn, user_id=user_id)
    preferences = {}
    selected = []
    for row in rows:
        proposed = preferences | {row.memory_key: row.memory_value}
        if len(json.dumps(proposed)) <= max_characters:
            preferences = proposed
            selected.append(str(row.id))
    return RetrievedMemory(preferences, tuple(selected))


def merge_plan_with_memory(current: TravelPlan | None, updates: dict,
                           preferences: dict[str, str] | None,
                           previous_defaults: dict[str, str] | None = None
                           ) -> tuple[TravelPlan, dict[str, str]]:
    """Return validated plan plus provenance for only the defaults we applied.

    Explicit updates must come from the analyzer's current-user delta. The prompt
    must not copy remembered values into that delta. Provenance allows subsequent
    retrievals to remove or refresh old memory defaults without erasing explicit
    trip choices. It does not write changes back to the durable profile.
    """
    data = current.model_dump() if current else TravelPlan().model_dump()
    for key, old_value in (previous_defaults or {}).items():
        if key in ALLOWED_VALUES and data.get(key) == old_value:
            data[key] = None
    explicit = {key: value for key, value in updates.items() if value is not None}
    data.update(explicit)
    applied = {}
    for key, value in (preferences or {}).items():
        if key not in ALLOWED_VALUES or value not in ALLOWED_VALUES[key]:
            continue
        if data.get(key) is None:
            data[key] = value
            applied[key] = value
    return TravelPlan.model_validate(data), applied
