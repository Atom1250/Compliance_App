"""Company management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.db.models import Company
from apps.api.app.db.session import get_db_session
from apps.api.app.services.audit import log_structured_event

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    employees: int | None = Field(default=None, ge=0)
    turnover: float | None = Field(default=None, ge=0)
    listed_status: bool | None = None
    reporting_year: int | None = Field(default=None, ge=1900, le=3000)


class CompanyItem(BaseModel):
    id: int
    name: str
    employees: int | None
    turnover: float | None
    listed_status: bool | None
    reporting_year: int | None


class CompanyCreateResponse(CompanyItem):
    pass


class CompanyListResponse(BaseModel):
    companies: list[CompanyItem]


@router.post("", response_model=CompanyCreateResponse)
def create_company(
    payload: CompanyCreateRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> CompanyCreateResponse:
    company = Company(
        tenant_id=auth.tenant_id,
        name=payload.name,
        employees=payload.employees,
        turnover=payload.turnover,
        listed_status=payload.listed_status,
        reporting_year=payload.reporting_year,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    log_structured_event(
        "company.created",
        tenant_id=auth.tenant_id,
        company_id=company.id,
        name=company.name,
    )

    return CompanyCreateResponse(
        id=company.id,
        name=company.name,
        employees=company.employees,
        turnover=company.turnover,
        listed_status=company.listed_status,
        reporting_year=company.reporting_year,
    )


@router.get("", response_model=CompanyListResponse)
def list_companies(
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> CompanyListResponse:
    rows = db.scalars(
        select(Company)
        .where(Company.tenant_id == auth.tenant_id)
        .order_by(Company.name.asc(), Company.id.asc())
    ).all()

    log_structured_event(
        "company.listed",
        tenant_id=auth.tenant_id,
        company_count=len(rows),
    )

    return CompanyListResponse(
        companies=[
            CompanyItem(
                id=row.id,
                name=row.name,
                employees=row.employees,
                turnover=row.turnover,
                listed_status=row.listed_status,
                reporting_year=row.reporting_year,
            )
            for row in rows
        ]
    )
