import pytest
from django.urls import reverse

from tests.helpers import ACCESS_PARAMS, assert_access, login_if_needed

CHARGE_PERMISSION = "billing.charge"


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [CHARGE_PERMISSION])],
)
@pytest.mark.django_db
def test_payment_period_preview__access(
    client,
    create_staff_user,
    create_client,
    create_plan,
    get_login_url,
    is_logged_in,
    permissions,
):
    affiliate = create_client()
    plan = create_plan()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:payment_preview", kwargs={"codigo_afiliado": affiliate.codigo_afiliado})
    response = client.get(url, {"plan_id": plan.pk})
    request_url = "{}?plan_id={}".format(url, plan.pk)
    assert_access(
        response, is_logged_in, permissions, CHARGE_PERMISSION, request_url, get_login_url
    )


@pytest.mark.parametrize(
    ("is_logged_in", "permissions"),
    ACCESS_PARAMS + [(True, [CHARGE_PERMISSION])],
)
@pytest.mark.django_db
def test_payment_success__access(
    client,
    create_staff_user,
    create_invoice,
    get_login_url,
    is_logged_in,
    permissions,
):
    invoice = create_invoice()
    login_if_needed(client, create_staff_user, is_logged_in, permissions)

    url = reverse("billing:payment_success", kwargs={"pk": invoice.pk})
    response = client.get(url)
    assert_access(
        response,
        is_logged_in,
        permissions,
        CHARGE_PERMISSION,
        url,
        get_login_url,
        success_status=302,
    )
    if is_logged_in and CHARGE_PERMISSION in permissions:
        assert response.url.startswith(
            reverse("billing:invoice_detail", kwargs={"pk": invoice.pk})
        )
