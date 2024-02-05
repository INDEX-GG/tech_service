from typing import List
from uuid import UUID

from src.models import CustomModel


class CompanyContacts(CustomModel):
    id: UUID
    phone: str
    person: str | None


class UserCompany(CustomModel):
    id: UUID
    name: str
    address: str | None
    opening_time: str | None
    closing_time: str | None
    only_weekdays: bool
    contacts: List[CompanyContacts] = []


class UserResponse(CustomModel):
    id: int
    username: str
    is_active: bool
    is_admin: bool
    is_customer: bool
    is_executor: bool
    name: str | None
    phone: str | None
    customer_company: UserCompany | None


class CustomerUserResponse(CustomModel):
    id: int
    username: str
    is_active: bool
    name: str | None
    phone: str | None
    customer_company: UserCompany | None


class CustomersList(CustomModel):
    id: int
    name: str
    address: str


class ExecutorsList(CustomModel):
    id: int
    name: str | None
    phone: str | None


class CustomersListPaginated(CustomModel):
    total: int
    customers: List[CustomersList]


class ExecutorUserResponse(CustomModel):
    id: int
    username: str
    is_active: bool
    name: str
    phone: str | None  # TODO: Check could it be None?


class ExecutorsListPaginated(CustomModel):
    total: int
    executors: List[ExecutorsList]


class CreateExecutorInput(CustomModel):
    username: str
    password: str
    name: str
    phone: str


class CustomerContacts(CustomModel):
    phone: str
    person: str


class CreateCustomerInput(CustomModel):
    username: str
    password: str
    name: str
    address: str
    opening_time: str
    closing_time: str
    only_weekdays: bool
    contacts: List[CustomerContacts]


class EditUserCredentials(CustomModel):
    username: str = None
    password: str = None


class EditUserPersonalData(CustomModel):
    name: str = None
    phone: str = None


class EditCustomerCompany(CustomModel):
    name: str = None
    address: str = None
    opening_time: str = None
    closing_time: str = None
    only_weekdays: bool = None


class EditCustomerContacts(CustomModel):
    phone: str
    person: str
