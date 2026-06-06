import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["dashboard.view"])],
)
@pytest.mark.django_db
def test_dashboard__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("dashboard")
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, "dashboard.view", url, get_login_url)
