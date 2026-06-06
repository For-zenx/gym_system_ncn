import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed

REQUIRED_PERMISSION = "access.view_logs"


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [REQUIRED_PERMISSION])],
)
@pytest.mark.django_db
def test_access_log_list__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("access:access_log_list")
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, REQUIRED_PERMISSION, url, get_login_url)
