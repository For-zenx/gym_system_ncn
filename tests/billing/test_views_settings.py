import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["settings.exchange_rate"])],
)
@pytest.mark.django_db
def test_exchange_rate_update__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:update_rate")
    response = client.post(url, {"tasa_ves": "120.50"})
    assert_access(
        response,
        is_logged_in,
        permissions,
        "settings.exchange_rate",
        url,
        get_login_url,
        success_status=302,
    )
