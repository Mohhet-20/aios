import pytest

from docs_platform.architecture.diagram_service import DiagramService
from docs_platform.core.exceptions import DiagramNotFoundError, UnsupportedDiagramTypeError

pytestmark = pytest.mark.asyncio


async def test_create_diagram_rejects_unsupported_type(repos):
    svc = DiagramService(repos)
    with pytest.raises(UnsupportedDiagramTypeError):
        await svc.create_diagram(diagram_type="not-a-type", title="X", tenant_id="t-arch")


async def test_create_and_list_diagrams(repos):
    svc = DiagramService(repos)
    await svc.create_diagram(tenant_id="t-arch", diagram_type="system_overview", title="System")
    await svc.create_diagram(tenant_id="t-arch", diagram_type="sequence", title="Login Flow")
    overview_only = await svc.list_diagrams("t-arch", diagram_type="system_overview")
    assert len(overview_only) == 1


async def test_related_diagrams_bfs(repos):
    svc = DiagramService(repos)
    system = await svc.create_diagram(tenant_id="t-arch", diagram_type="system_overview", title="System")
    component = await svc.create_diagram(
        tenant_id="t-arch", diagram_type="component", title="Components", related_refs=[system.id]
    )
    service_map = await svc.create_diagram(
        tenant_id="t-arch", diagram_type="service_map", title="Services", related_refs=[component.id]
    )
    related = await svc.related_diagrams("t-arch", system.id)
    related_ids = {d.id for d in related}
    assert component.id in related_ids
    assert service_map.id in related_ids


async def test_get_or_404_cross_tenant(repos):
    svc = DiagramService(repos)
    diagram = await svc.create_diagram(tenant_id="t-arch", diagram_type="deployment", title="Deploy")
    with pytest.raises(DiagramNotFoundError):
        await svc.get_or_404("other-tenant", diagram.id)
