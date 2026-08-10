from __future__ import annotations

from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

DATE_FORMAT_MESSAGE = "Date values must use YYYY-MM-DD format."


def validate_optional_date(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return ""

    try:
        date.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError(f"{field_name}: {DATE_FORMAT_MESSAGE}") from exc

    return normalized_value


def validate_date_range(
    start_value: str | None,
    end_value: str | None,
) -> None:
    if not start_value or not end_value:
        return

    if date.fromisoformat(end_value) < date.fromisoformat(start_value):
        raise ValueError(
            "Authorization end date cannot be before " "the authorization start date."
        )


class AuthBase(BaseModel):
    facility: str
    client_name: str
    member_id: str = ""
    auth_number: str = ""
    group_number: str = ""
    date_of_birth: str = ""
    loc: str
    insurance: str = ""
    insurance_phone: str = ""
    insurance_fax: str = ""
    submission_methods: str
    portal_name: str = ""
    fax_numbers: str = ""
    live_call_type: str = ""
    scheduled_call_at: str = ""
    care_manager_enabled: bool = False
    care_manager_details: str = ""
    requested_days: int = Field(default=0, ge=0)
    approved_days: int = Field(default=0, ge=0)
    notes_links: str = ""
    auth_type: str
    status: str
    discharge_clinical_needed: bool = False
    no_pa_required: bool = False
    progress_made: bool = False
    facility_informed: bool = False
    waiting_on_clinicals: bool = False
    los_requested: str = ""
    days_approved: str = ""
    auth_start_date: str = ""
    auth_end_date: str = ""
    programming_days: str = ""
    review_due_date: str = ""
    submitted_at: str | None = None
    decision_at: str | None = None

    @field_validator(
        "date_of_birth",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
        mode="before",
    )
    @classmethod
    def validate_date_fields(
        cls,
        value: str | None,
        info,
    ) -> str | None:
        return validate_optional_date(
            value,
            field_name=info.field_name,
        )

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(
        cls,
        value: str,
    ) -> str:
        if value and date.fromisoformat(value) > date.today():
            raise ValueError("Date of birth cannot be in the future.")

        return value

    @model_validator(mode="after")
    def validate_authorization_dates(self) -> AuthBase:
        validate_date_range(
            self.auth_start_date,
            self.auth_end_date,
        )

        return self


class AuthCreate(AuthBase):
    model_config = ConfigDict(extra="forbid")


class AuthUpdate(BaseModel):
    facility: str | None = None
    client_name: str | None = None
    member_id: str | None = None
    auth_number: str | None = None
    group_number: str | None = None
    date_of_birth: str | None = None
    loc: str | None = None
    insurance: str | None = None
    insurance_phone: str | None = None
    insurance_fax: str | None = None
    submission_methods: str | None = None
    portal_name: str | None = None
    fax_numbers: str | None = None
    live_call_type: str | None = None
    scheduled_call_at: str | None = None
    care_manager_enabled: bool | None = None
    care_manager_details: str | None = None
    notes_links: str | None = None
    auth_type: str | None = None
    status: str | None = None
    discharge_clinical_needed: bool | None = None
    no_pa_required: bool | None = None
    progress_made: bool | None = None
    facility_informed: bool | None = None
    waiting_on_clinicals: bool | None = None
    los_requested: str | None = None
    days_approved: str | None = None
    auth_start_date: str | None = None
    auth_end_date: str | None = None
    programming_days: str | None = None
    submitted_at: str | None = None
    review_due_date: str | None = None
    decision_at: str | None = None
    requested_days: int | None = Field(default=None, ge=0)
    approved_days: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "date_of_birth",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
        mode="before",
    )
    @classmethod
    def validate_date_fields(
        cls,
        value: str | None,
        info,
    ) -> str | None:
        return validate_optional_date(
            value,
            field_name=info.field_name,
        )

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(
        cls,
        value: str | None,
    ) -> str | None:
        if value and date.fromisoformat(value) > date.today():
            raise ValueError("Date of birth cannot be in the future.")

        return value

    @model_validator(mode="after")
    def validate_authorization_dates(self) -> AuthUpdate:
        validate_date_range(
            self.auth_start_date,
            self.auth_end_date,
        )

        return self


class AuthRecord(AuthBase):
    id: int
    care_manager_enabled: bool = Field(default=False)
    discharge_clinical_needed: bool = Field(default=False)
    no_pa_required: bool = Field(default=False)
    progress_made: bool = Field(default=False)
    facility_informed: bool = Field(default=False)
    waiting_on_clinicals: bool = Field(default=False)
    created_at: str
    updated_at: str


class AuthListResponse(BaseModel):
    auths: list[AuthRecord]


class AuthEventBase(BaseModel):
    event_type: str
    event_date: str
    event_time: str = ""
    outcome: str = ""
    notes: str = ""
    requested_days: int = Field(default=0, ge=0)
    approved_days: int = Field(default=0, ge=0)
    auth_start_date: str = ""
    auth_end_date: str = ""
    review_due_date: str = ""

    @field_validator(
        "event_date",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
        mode="before",
    )
    @classmethod
    def validate_date_fields(
        cls,
        value: str | None,
        info,
    ) -> str | None:
        return validate_optional_date(
            value,
            field_name=info.field_name,
        )

    @model_validator(mode="after")
    def validate_authorization_dates(self) -> AuthEventBase:
        validate_date_range(
            self.auth_start_date,
            self.auth_end_date,
        )

        return self


class AuthEventCreate(AuthEventBase):
    model_config = ConfigDict(extra="forbid")


class AuthEventUpdate(BaseModel):
    event_type: str | None = None
    event_date: str | None = None
    event_time: str | None = None
    outcome: str | None = None
    notes: str | None = None
    requested_days: int | None = Field(default=None, ge=0)
    approved_days: int | None = Field(default=None, ge=0)
    auth_start_date: str | None = None
    auth_end_date: str | None = None
    review_due_date: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "event_date",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
        mode="before",
    )
    @classmethod
    def validate_date_fields(
        cls,
        value: str | None,
        info,
    ) -> str | None:
        return validate_optional_date(
            value,
            field_name=info.field_name,
        )

    @model_validator(mode="after")
    def validate_authorization_dates(
        self,
    ) -> AuthEventUpdate:
        validate_date_range(
            self.auth_start_date,
            self.auth_end_date,
        )

        return self


class AuthEventRecord(AuthEventBase):
    id: int
    auth_id: int
    created_at: str
    updated_at: str


class AuthEventListResponse(BaseModel):
    events: list[AuthEventRecord]


class DeleteResponse(BaseModel):
    deleted: bool
    id: int


class AnalyticsSummaryResponse(BaseModel):
    total_auths: int
    by_status: dict[str, int]
    by_loc: dict[str, int]
    by_auth_type: dict[str, int]
    no_pa_required: int
    waiting_on_clinicals: int
