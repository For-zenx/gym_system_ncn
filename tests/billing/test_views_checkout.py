import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed

CHARGE_PERMISSION = "billing.charge"
CUT_DATE_PERMISSION = "billing.change_cut_date"


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [CHARGE_PERMISSION])],
)
@pytest.mark.django_db
def test_charge_checkout__access(
    client,
    create_staff_user,
    create_client,
    create_plan,
    get_login_url,
    is_logged_in,
    permissions,
):
    affiliate = create_client()
    create_plan()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:charge_checkout", kwargs={"codigo_afiliado": affiliate.codigo_afiliado})
    response = client.get(url)
    assert_access(response, is_logged_in, permissions, CHARGE_PERMISSION, url, get_login_url)


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [CHARGE_PERMISSION])],
)
@pytest.mark.django_db
def test_renew_plan__access(
    client,
    create_staff_user,
    create_client,
    get_login_url,
    is_logged_in,
    permissions,
):
    affiliate = create_client()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:renew_plan", kwargs={"codigo_afiliado": affiliate.codigo_afiliado})
    response = client.post(url, {"origin": "profile"})
    assert_access(
        response,
        is_logged_in,
        permissions,
        CHARGE_PERMISSION,
        url,
        get_login_url,
        success_status=302,
    )


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [CUT_DATE_PERMISSION])],
)
@pytest.mark.django_db
def test_change_cut_date__access(
    client,
    create_staff_user,
    create_client,
    get_login_url,
    is_logged_in,
    permissions,
):
    affiliate = create_client()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:change_cut_date", kwargs={"codigo_afiliado": affiliate.codigo_afiliado})
    response = client.post(url, {"cut_day": "15"})
    assert_access(
        response,
        is_logged_in,
        permissions,
        CUT_DATE_PERMISSION,
        url,
        get_login_url,
        success_status=302,
    )
    if is_logged_in and CUT_DATE_PERMISSION in permissions:
        assert response.url == reverse(
            "clients:profile",
            kwargs={"codigo_afiliado": affiliate.codigo_afiliado},
        )
