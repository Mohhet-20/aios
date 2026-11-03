import pytest

from workflow_platform.domain.enums import NodeType
from workflow_platform.node_library.registry import NODE_TYPE_SPECS, seed_node_definitions


def test_node_type_specs_cover_every_enum_value():
    assert {s.key for s in NODE_TYPE_SPECS} == {n.value for n in NodeType}


@pytest.mark.asyncio
async def test_seed_node_definitions_is_idempotent(repos):
    first = await seed_node_definitions(repos)
    assert first == len(NODE_TYPE_SPECS)

    second = await seed_node_definitions(repos)
    assert second == 0

    all_defs = await repos.node_definitions.list(limit=100)
    assert len(all_defs) == len(NODE_TYPE_SPECS)
