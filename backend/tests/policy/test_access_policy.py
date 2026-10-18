"""Tests unitarios puros de la politica central de permisos (PR-03.1).

No usan base de datos ni el cliente HTTP. El modulo `access_policy` no debe importar
fastapi ni sqlalchemy (ver test_access_policy_purity.py).
"""

import pytest
from access_policy import (
    MSG_FORBIDDEN,
    MSG_MANAGED_READONLY,
    MSG_NO_ACCESS,
    MSG_SUSPENDED,
    MSG_SWITCH_COMPANY,
    MSG_VIEW_AS_READONLY,
    ROLE_MANAGER,
    ROLE_PLATFORM_ADMIN,
    ROLE_WORKER,
    CompanyFacts,
    PolicyError,
    assert_view_as_read_only,
    authorize_company,
    can_edit_member_rates,
    can_edit_member_settings,
    can_write_work_log,
    normalize_member_role,
    require_platform_admin,
)

COMPANY_ID = "company-a"
OTHER_COMPANY_ID = "company-b"
ALLOWLISTED_PATHS = ["/auth/switch-scope", "/logout", "/refresh-token"]


def _facts(
    *,
    company_id: str = COMPANY_ID,
    exists: bool = True,
    is_active: bool = True,
    is_managed: bool = False,
    membership_active: bool = True,
    membership_role: str | None = ROLE_WORKER,
) -> CompanyFacts:
    return CompanyFacts(
        company_id=company_id,
        exists=exists,
        is_active=is_active,
        is_managed=is_managed,
        membership_active=membership_active,
        membership_role=membership_role,
    )


def _missing_company_facts() -> CompanyFacts:
    return _facts(exists=False, membership_active=False, membership_role=None)


def _assert_policy_error(exc_info: pytest.ExceptionInfo, status_code: int, detail: str) -> None:
    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail


# ---------------------------------------------------------------------------
# authorize_company: casos no PA
# ---------------------------------------------------------------------------


def test_non_admin_on_missing_company_gets_no_access_403():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=COMPANY_ID,
            facts=_missing_company_facts(),
            min_role=ROLE_WORKER,
        )
    _assert_policy_error(exc_info, 403, MSG_NO_ACCESS)


def test_non_admin_without_membership_gets_no_access_403():
    facts = _facts(membership_active=False, membership_role=None)
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=COMPANY_ID,
            facts=facts,
            min_role=ROLE_WORKER,
        )
    _assert_policy_error(exc_info, 403, MSG_NO_ACCESS)


def test_non_admin_with_inactive_membership_gets_no_access_403():
    facts = _facts(membership_active=False, membership_role=ROLE_MANAGER)
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=COMPANY_ID,
            facts=facts,
            min_role=ROLE_WORKER,
        )
    _assert_policy_error(exc_info, 403, MSG_NO_ACCESS)


def test_active_member_of_suspended_company_gets_suspended_403():
    facts = _facts(is_active=False, membership_active=True, membership_role=ROLE_MANAGER)
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=COMPANY_ID,
            facts=facts,
            min_role=ROLE_MANAGER,
        )
    _assert_policy_error(exc_info, 403, MSG_SUSPENDED)


def test_worker_below_min_role_manager_gets_forbidden_403():
    facts = _facts(membership_role=ROLE_WORKER)
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=COMPANY_ID,
            facts=facts,
            min_role=ROLE_MANAGER,
        )
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


def test_manager_with_other_token_company_gets_switch_company_403():
    facts = _facts(membership_role=ROLE_MANAGER)
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=False,
            token_company_id=OTHER_COMPANY_ID,
            facts=facts,
            min_role=ROLE_MANAGER,
        )
    _assert_policy_error(exc_info, 403, MSG_SWITCH_COMPANY)


def test_manager_with_matching_token_company_returns_manager():
    facts = _facts(membership_role=ROLE_MANAGER)
    result = authorize_company(
        is_platform_admin=False,
        token_company_id=COMPANY_ID,
        facts=facts,
        min_role=ROLE_MANAGER,
    )
    assert result == ROLE_MANAGER


def test_membership_admin_role_is_normalized_to_manager_in_authorization():
    membership_role = normalize_member_role("admin")
    facts = _facts(membership_role=membership_role)
    result = authorize_company(
        is_platform_admin=False,
        token_company_id=COMPANY_ID,
        facts=facts,
        min_role=ROLE_MANAGER,
    )
    assert result == ROLE_MANAGER


# ---------------------------------------------------------------------------
# authorize_company: platform admin sin modo "ver como"
# ---------------------------------------------------------------------------


def test_platform_admin_on_missing_company_gets_not_found_404():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=True,
            token_company_id=COMPANY_ID,
            facts=_missing_company_facts(),
            min_role=ROLE_WORKER,
        )
    _assert_policy_error(exc_info, 404, "Empresa no encontrada")


def test_platform_admin_on_suspended_company_returns_platform_admin_role():
    facts = _facts(is_active=False, membership_active=False, membership_role=None)
    result = authorize_company(
        is_platform_admin=True,
        token_company_id=COMPANY_ID,
        facts=facts,
        min_role=ROLE_MANAGER,
    )
    assert result == ROLE_PLATFORM_ADMIN


# ---------------------------------------------------------------------------
# authorize_company: modo "ver como" (view_as)
# ---------------------------------------------------------------------------


def test_view_as_worker_on_manager_min_role_gets_forbidden_403():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=True,
            view_as=ROLE_WORKER,
            token_company_id=COMPANY_ID,
            facts=_facts(),
            min_role=ROLE_MANAGER,
        )
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


def test_view_as_worker_on_worker_min_role_returns_worker():
    result = authorize_company(
        is_platform_admin=True,
        view_as=ROLE_WORKER,
        token_company_id=COMPANY_ID,
        facts=_facts(),
        min_role=ROLE_WORKER,
    )
    assert result == ROLE_WORKER


def test_view_as_manager_on_manager_min_role_with_matching_company_returns_manager():
    result = authorize_company(
        is_platform_admin=True,
        view_as=ROLE_MANAGER,
        token_company_id=COMPANY_ID,
        facts=_facts(),
        min_role=ROLE_MANAGER,
    )
    assert result == ROLE_MANAGER


def test_view_as_manager_on_platform_admin_min_role_gets_forbidden_403():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=True,
            view_as=ROLE_MANAGER,
            token_company_id=COMPANY_ID,
            facts=_facts(),
            min_role=ROLE_PLATFORM_ADMIN,
        )
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


def test_view_as_on_missing_company_gets_not_found_404():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=True,
            view_as=ROLE_WORKER,
            token_company_id=COMPANY_ID,
            facts=_missing_company_facts(),
            min_role=ROLE_WORKER,
        )
    _assert_policy_error(exc_info, 404, "Empresa no encontrada")


def test_view_as_manager_with_other_token_company_gets_switch_company_403():
    with pytest.raises(PolicyError) as exc_info:
        authorize_company(
            is_platform_admin=True,
            view_as=ROLE_MANAGER,
            token_company_id=OTHER_COMPANY_ID,
            facts=_facts(),
            min_role=ROLE_MANAGER,
        )
    _assert_policy_error(exc_info, 403, MSG_SWITCH_COMPANY)


# ---------------------------------------------------------------------------
# assert_view_as_read_only
# ---------------------------------------------------------------------------


def test_view_as_worker_post_to_work_logs_is_rejected_read_only_403():
    with pytest.raises(PolicyError) as exc_info:
        assert_view_as_read_only(ROLE_WORKER, "POST", "/work-logs")
    _assert_policy_error(exc_info, 403, MSG_VIEW_AS_READONLY)


def test_view_as_worker_get_is_allowed():
    assert_view_as_read_only(ROLE_WORKER, "GET", "/work-logs")


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_view_as_safe_methods_are_allowed(method):
    assert_view_as_read_only(ROLE_MANAGER, method, "/companies/1/members")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_view_as_manager_unsafe_methods_are_rejected(method):
    with pytest.raises(PolicyError) as exc_info:
        assert_view_as_read_only(ROLE_MANAGER, method, "/companies/1/members")
    _assert_policy_error(exc_info, 403, MSG_VIEW_AS_READONLY)


@pytest.mark.parametrize("path", ALLOWLISTED_PATHS)
def test_view_as_post_to_allowlisted_path_is_allowed(path):
    assert_view_as_read_only(ROLE_WORKER, "POST", path)


def test_without_view_as_write_is_allowed():
    assert_view_as_read_only(None, "POST", "/work-logs")


# ---------------------------------------------------------------------------
# require_platform_admin
# ---------------------------------------------------------------------------


def test_require_platform_admin_rejects_non_admin_with_forbidden_403():
    with pytest.raises(PolicyError) as exc_info:
        require_platform_admin(False)
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


def test_require_platform_admin_accepts_platform_admin():
    assert require_platform_admin(True) is None


# ---------------------------------------------------------------------------
# can_write_work_log
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", [ROLE_PLATFORM_ADMIN, ROLE_MANAGER])
def test_can_write_work_log_admin_roles_are_always_allowed(role):
    assert can_write_work_log(role=role, is_managed=True, is_owner=False) is None


def test_worker_cannot_write_work_log_in_managed_company():
    with pytest.raises(PolicyError) as exc_info:
        can_write_work_log(role=ROLE_WORKER, is_managed=True, is_owner=True)
    _assert_policy_error(exc_info, 403, MSG_MANAGED_READONLY)


def test_worker_owner_can_write_work_log_in_unmanaged_company():
    assert can_write_work_log(role=ROLE_WORKER, is_managed=False, is_owner=True) is None


def test_worker_not_owner_cannot_write_work_log_in_unmanaged_company():
    with pytest.raises(PolicyError) as exc_info:
        can_write_work_log(role=ROLE_WORKER, is_managed=False, is_owner=False)
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


# ---------------------------------------------------------------------------
# can_edit_member_rates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", [ROLE_PLATFORM_ADMIN, ROLE_MANAGER])
def test_can_edit_member_rates_admin_roles_are_allowed_in_managed_company(role):
    assert can_edit_member_rates(role=role, is_managed=True, is_self=False) is None


def test_worker_cannot_edit_rates_of_another_member():
    with pytest.raises(PolicyError) as exc_info:
        can_edit_member_rates(role=ROLE_WORKER, is_managed=False, is_self=False)
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


def test_worker_cannot_edit_own_rates_in_managed_company():
    with pytest.raises(PolicyError) as exc_info:
        can_edit_member_rates(role=ROLE_WORKER, is_managed=True, is_self=True)
    _assert_policy_error(exc_info, 403, MSG_MANAGED_READONLY)


def test_worker_can_edit_own_rates_in_unmanaged_company():
    assert can_edit_member_rates(role=ROLE_WORKER, is_managed=False, is_self=True) is None


def test_worker_editing_another_member_in_managed_company_gets_forbidden_first():
    # Orden de comprobacion: primero la identidad (is_self) y despues is_managed.
    with pytest.raises(PolicyError) as exc_info:
        can_edit_member_rates(role=ROLE_WORKER, is_managed=True, is_self=False)
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


# ---------------------------------------------------------------------------
# can_edit_member_settings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", [ROLE_PLATFORM_ADMIN, ROLE_MANAGER])
def test_can_edit_member_settings_admin_roles_are_allowed_for_others(role):
    assert can_edit_member_settings(role=role, is_self=False) is None


def test_worker_can_edit_own_member_settings():
    assert can_edit_member_settings(role=ROLE_WORKER, is_self=True) is None


def test_worker_cannot_edit_another_member_settings():
    with pytest.raises(PolicyError) as exc_info:
        can_edit_member_settings(role=ROLE_WORKER, is_self=False)
    _assert_policy_error(exc_info, 403, MSG_FORBIDDEN)


# ---------------------------------------------------------------------------
# normalize_member_role
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_role", "expected"),
    [
        ("admin", ROLE_MANAGER),
        ("manager", ROLE_MANAGER),
        ("worker", ROLE_WORKER),
        ("platform_admin", None),
        ("viewer", None),
        (None, None),
    ],
    ids=["admin", "manager", "worker", "platform_admin_unknown", "unknown", "none"],
)
def test_normalize_member_role(raw_role, expected):
    assert normalize_member_role(raw_role) == expected


# ---------------------------------------------------------------------------
# PolicyError
# ---------------------------------------------------------------------------


def test_policy_error_exposes_status_code_and_detail():
    error = PolicyError(403, MSG_NO_ACCESS)
    assert isinstance(error, Exception)
    assert error.status_code == 403
    assert error.detail == MSG_NO_ACCESS
