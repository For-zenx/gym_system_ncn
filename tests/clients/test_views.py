import pytest
from django.urls import reverse

REQUIRED_PERMISSION = "clients.view_list"


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    [
        (False, []),
        (True, []),
        (True, [REQUIRED_PERMISSION]),
    ],
)
@pytest.mark.django_db
def test_client_list__access(
    client,
    create_staff_user,
    create_client,
    get_login_url,
    is_logged_in,
    permissions,
):
    create_client()
    if is_logged_in:
        staff = create_staff_user(permissions=permissions)
        client.force_login(staff)

    url = reverse("clients:client_list")
    response = client.get(url)

    if not is_logged_in:
        assert response.status_code == 302
        assert response.url == get_login_url(url)
    elif REQUIRED_PERMISSION not in permissions:
        assert response.status_code == 403
    else:
        assert response.status_code == 200
