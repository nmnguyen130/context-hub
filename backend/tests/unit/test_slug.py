import pytest

from app.modules.tenant.services.tenant_service import TenantService


@pytest.mark.unit
def test_slug_from_name():
    assert TenantService.generate_slug("My Company LLC") == "my-company-llc"
    assert TenantService.generate_slug("  Space   and  Dash- ") == "space-and-dash"
    assert (
        TenantService.generate_slug("!!!Special Characters@#$") == "special-characters"
    )
    assert TenantService.generate_slug("") == "organization"
