import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["products.view"])],
)
@pytest.mark.django_db
def test_product_list__access(
    client,
    create_staff_user,
    create_sale_item,
    get_login_url,
    is_logged_in,
    permissions,
):
    create_sale_item()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:product_list")
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, "products.view", url, get_login_url)


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["products.manage"])],
)
@pytest.mark.django_db
def test_product_create__access(
    client,
    create_staff_user,
    get_login_url,
    is_logged_in,
    permissions,
):
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:product_create")
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, "products.manage", url, get_login_url)


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["products.manage"])],
)
@pytest.mark.django_db
def test_product_update__access(
    client,
    create_staff_user,
    create_sale_item,
    get_login_url,
    is_logged_in,
    permissions,
):
    item = create_sale_item()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:product_update", kwargs={"pk": item.pk})
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, "products.manage", url, get_login_url)


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, ["products.manage"])],
)
@pytest.mark.django_db
def test_product_delete__access(
    client,
    create_staff_user,
    create_sale_item,
    get_login_url,
    is_logged_in,
    permissions,
):
    item = create_sale_item()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:product_delete", kwargs={"pk": item.pk})
    response = client.post(url)
    assert_access(
        response,
        is_logged_in,
        permissions,
        "products.manage",
        url,
        get_login_url,
        success_status=302,
    )
    if is_logged_in and "products.manage" in permissions:
        assert response.url == reverse("billing:product_list")
