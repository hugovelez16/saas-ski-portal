"""
Pruebas unitarias para CreateWorkLogUseCase utilizando mocks de los puertos de repositorio.
"""
from datetime import date, time
from decimal import Decimal
import pytest
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember, CompanyRole
from domain.entities.work_log import WorkLog
from domain.ports.repositories.work_log_repository_port import WorkLogRepositoryPort, CompanyRepositoryPort, CompanyMemberRepositoryPort
from domain.exceptions.domain_exceptions import InactiveMembershipException, EntityNotFoundException
from application.use_cases.work_logs.create_work_log_use_case import CreateWorkLogUseCase


class InMemoryCompanyRepo(CompanyRepositoryPort):
    def __init__(self):
        self.companies = {}

    async def get_by_id(self, company_id: str):
        return self.companies.get(company_id)

    async def get_by_name(self, name: str):
        return next((c for c in self.companies.values() if c.name == name), None)

    async def list_companies(self):
        return list(self.companies.values())

    async def save(self, company: Company):
        self.companies[company.id] = company
        return company


class InMemoryCompanyMemberRepo(CompanyMemberRepositoryPort):
    def __init__(self):
        self.members = {}

    async def get_membership(self, user_id: str, company_id: str):
        return self.members.get((user_id, company_id))

    async def list_members_by_company(self, company_id: str):
        return [m for (u, c), m in self.members.items() if c == company_id]

    async def list_companies_by_user(self, user_id: str):
        return [m for (u, c), m in self.members.items() if u == user_id]

    async def save(self, member: CompanyMember):
        self.members[(member.user_id, member.company_id)] = member
        return member


class InMemoryWorkLogRepo(WorkLogRepositoryPort):
    def __init__(self):
        self.logs = {}

    async def get_by_id(self, log_id: str):
        return self.logs.get(log_id)

    async def list_logs(self, **kwargs):
        return list(self.logs.values())

    async def save(self, log: WorkLog):
        self.logs[log.id] = log
        return log

    async def save_bulk(self, logs):
        for l in logs:
            self.logs[l.id] = l
        return logs

    async def delete(self, log_id: str):
        if log_id in self.logs:
            del self.logs[log_id]
            return True
        return False


@pytest.mark.anyio
async def test_create_work_log_success():
    company_repo = InMemoryCompanyRepo()
    member_repo = InMemoryCompanyMemberRepo()
    work_log_repo = InMemoryWorkLogRepo()

    company = Company(
        id="comp-1",
        name="Sierra Nevada Ski School",
        tax_config={"irpf_base": 0.15, "social_security": 0.05},
        worklog_definitions={"clase_particular": {"unit": "hours", "is_range": False}},
    )
    await company_repo.save(company)

    member = CompanyMember(
        user_id="user-1",
        company_id="comp-1",
        role=CompanyRole.WORKER,
        is_active=True,
        rates_config={"clase_particular": {"base_rate": 30.0, "is_gross": False}},
    )
    await member_repo.save(member)

    use_case = CreateWorkLogUseCase(
        work_log_repo=work_log_repo,
        company_repo=company_repo,
        member_repo=member_repo,
    )

    result = await use_case.execute(
        user_id="user-1",
        company_id="comp-1",
        log_type="clase_particular",
        start_date=date(2026, 1, 15),
        start_time=time(10, 0),
        end_time=time(12, 0),
        duration_hours=2.0,
        description="Clase particular de esqui alpino",
    )

    assert result is not None
    assert result.user_id == "user-1"
    assert result.company_id == "comp-1"
    assert result.net_amount.amount == Decimal("60.00")
    # Bruto = 60 / (1 - 0.20) = 75.00
    assert result.gross_amount.amount == Decimal("75.00")
    assert result.duration_hours == 2.0


@pytest.mark.anyio
async def test_create_work_log_inactive_member_raises():
    company_repo = InMemoryCompanyRepo()
    member_repo = InMemoryCompanyMemberRepo()
    work_log_repo = InMemoryWorkLogRepo()

    company = Company(id="comp-1", name="Escuela")
    await company_repo.save(company)

    member = CompanyMember(
        user_id="user-1",
        company_id="comp-1",
        role=CompanyRole.WORKER,
        is_active=False,
    )
    await member_repo.save(member)

    use_case = CreateWorkLogUseCase(
        work_log_repo=work_log_repo,
        company_repo=company_repo,
        member_repo=member_repo,
    )

    with pytest.raises(InactiveMembershipException):
        await use_case.execute(
            user_id="user-1",
            company_id="comp-1",
            log_type="clase",
            start_date=date(2026, 1, 15),
        )
