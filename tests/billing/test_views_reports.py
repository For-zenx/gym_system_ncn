import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["reports.view"])],
)
@pytest.mark.django_db
def test_report_view__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:report")
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, "reports.view", url, get_login_url)


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["reports.send"])],
)
@pytest.mark.django_db
def test_report_send__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:report_send")
    response = client.post(url, {"period_days": "7"})
    assert_access(
        response,
        is_logged_in,
        permissions,
        "reports.send",
        url,
        get_login_url,
        success_status=302,
    )
