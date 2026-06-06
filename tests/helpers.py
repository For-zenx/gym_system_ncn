ACCESS_PARAMS = [
    (False, []),
    (True, []),
]


def login_if_needed(client, create_staff_user, is_logged_in, permissions):
    if is_logged_in:
        staff = create_staff_user(permissions=permissions)
        client.force_login(staff)


def assert_access(
    response,
    is_logged_in,
    permissions,
    required_permission,
    url,
    get_login_url,
    success_status=200,
):
    if not is_logged_in:
        assert response.status_code == 302
        assert response.url == get_login_url(url)
    elif required_permission not in permissions:
        assert response.status_code == 403
    else:
        assert response.status_code == success_status


def assert_any_permission_access(
    response,
    is_logged_in,
    permissions,
    allowed_permissions,
    url,
    get_login_url,
    success_status=200,
):
    if not is_logged_in:
        assert response.status_code == 302
        assert response.url == get_login_url(url)
    elif not any(code in permissions for code in allowed_permissions):
        assert response.status_code == 403
    else:
        assert response.status_code == success_status
