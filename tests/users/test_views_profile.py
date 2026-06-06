import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed


@pytest.mark.parametrize("is_logged_in", [False, True])
@pytest.mark.django_db
def test_staff_profile_get__access(client, create_staff_user, get_login_url, is_logged_in):
    if is_logged_in:
        staff = create_staff_user(permissions=["dashboard.view"])
        client.force_login(staff)

    url = reverse("staff_profile")
    response = client.get(url)

    if not is_logged_in:
        assert response.status_code == 302
        assert response.url == get_login_url(url)
    else:
        assert response.status_code == 200


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["users.edit"])],
)
@pytest.mark.django_db
def test_staff_profile_post__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    if is_logged_in:
        staff = create_staff_user(permissions=permissions)
        client.force_login(staff)

    url = reverse("staff_profile")
    response = client.post(url, {"display_name": "Nombre Actualizado"})
    assert_access(
        response,
        is_logged_in,
        permissions,
        "users.edit",
        url,
        get_login_url,
        success_status=302,
    )
