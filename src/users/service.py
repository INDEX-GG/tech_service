import uuid
from typing import Any, Dict, Coroutine

from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import User, Company, CompanyContacts
from src.users.schemas import CreateExecutorInput, CreateCustomerInput, EditUserCredentials, EditUserPersonalData


async def get_user_profile_by_id(user_id: int, session: AsyncSession) -> dict[str, Any] | None:
    select_query = select(User).where(User.id == user_id).options(
        selectinload(User.customer_company).selectinload(Company.contacts))
    model = await session.execute(select_query)
    user = model.scalar_one_or_none()
    return user


async def get_user_by_role(user_id: int, role: str, session: AsyncSession) -> dict[str, Any] | None:
    select_query = select(User).where(User.id == user_id)

    if role == "is_customer":
        select_query = select_query.where(User.is_customer, User.is_active).options(
            selectinload(User.customer_company).selectinload(Company.contacts))
    elif role == "is_executor":
        select_query = select_query.where(User.is_executor, User.is_active)

    user = await session.execute(select_query)
    response = user.scalar_one_or_none()
    return response


async def get_customers(search: str, offset: int, limit: int, session: AsyncSession) -> dict[str, Any] | None:
    search_conditions = []

    if search:
        search_conditions.append(or_(
            Company.name.ilike(f"%{search}%"),
            Company.address.ilike(f"%{search}%")
        ))

    base_condition = User.is_customer

    if search_conditions:
        base_condition = and_(base_condition, *search_conditions)

    count_query = (
        select(func.count())
        .select_from(User)
        .join(Company, User.customer_company)
        .where(base_condition, User.is_active)
    )

    total_records = await session.execute(count_query)
    total = total_records.scalar()

    select_query = (
        select(User.id, Company.name, Company.address)
        .join(Company)
        .where(base_condition, User.is_active)
        .offset(offset)
        .limit(limit)
    )

    customers = await session.execute(select_query)
    response = customers.fetchall()

    response_data = []
    for user_id, company_name, company_address in response:
        response_data.append({
            "id": user_id,
            "name": company_name,
            "address": company_address
        })

    response = {
        "total": total,
        "customers": response_data
    }
    return response


async def get_executors(search: str, offset: int, limit: int, session: AsyncSession) -> dict[str, Any] | None:
    search_conditions = []

    if search:
        search_conditions.append(or_(
            User.name.ilike(f"%{search}%"),
            User.phone.ilike(f"%{search}%")
        ))

    base_condition = User.is_executor == True

    if search_conditions:
        base_condition = and_(base_condition, *search_conditions)

    count_query = (
        select(func.count())
        .select_from(User)
        .where(base_condition, User.is_active)
    )

    total_records = await session.execute(count_query)
    total = total_records.scalar()

    select_query = (
        select(User.id, User.name, User.phone)
        .where(base_condition, User.is_active)
        .offset(offset)
        .limit(limit)
    )

    executors = await session.execute(select_query)
    response = executors.fetchall()

    response_data = []
    for user in response:
        response_data.append({
            "id": user.id,
            "name": user.name,
            "phone": user.phone
        })

    response = {
        "total": total,
        "executors": response_data
    }
    return response


async def create_executor(executor_data: CreateExecutorInput, session: AsyncSession) -> dict[str, Any] | None:
    executor = User(
        username=executor_data.username,
        password=executor_data.password,
        is_active=True,
        is_executor=True,
        name=executor_data.name,
        phone=executor_data.phone,
    )

    session.add(executor)
    await session.commit()
    await session.refresh(executor)

    return executor


async def create_customer(customer_data: CreateCustomerInput, session: AsyncSession) -> dict[str, Any] | None:
    try:
        customer = User(
            username=customer_data.username,
            password=customer_data.password,
            is_active=True,
            is_customer=True,
        )

        session.add(customer)
        await session.commit()
        await session.refresh(customer)

        customer_company = Company(
            user_id=customer.id,
            name=customer_data.name,
            address=customer_data.address,
            opening_time=customer_data.opening_time,
            closing_time=customer_data.closing_time,
            only_weekdays=customer_data.only_weekdays,
        )

        session.add(customer_company)
        await session.commit()
        await session.refresh(customer_company)

        for contact in customer_data.contacts:
            company_contact = CompanyContacts(
                company_id=customer_company.id,
                phone=contact.phone,
                person=contact.person,
            )
            session.add(company_contact)

        await session.commit()
        return customer

    except Exception as e:
        # Обработка ошибок
        print(f"Error creating customer: {e}")
        await session.rollback()
        return None
    finally:
        # Не забудьте закрыть сессию после выполнения операций
        await session.close()


async def block_user(user_id: int, session: AsyncSession) -> bool:
    try:
        select_query = select(User).where(User.id == user_id)
        model = await session.execute(select_query)
        user = model.scalar_one_or_none()

        if user:
            if user.is_active:
                user.is_active = False
                await session.commit()
                return True

        return False
    except:
        return False


async def edit_credentials(user_id: int, user_data: EditUserCredentials, session: AsyncSession) -> dict[str, Any] | None:
    try:
        user = await get_user_profile_by_id(user_id, session)

        if user:
            if user.is_active:
                if not user_data:
                    return None

                if user_data.username:
                    user.username = user_data.username
                if user_data.password:
                    user.password = user_data.password

                await session.commit()
                await session.refresh(user)
                return user
        return None
    except:
        return None


async def edit_personal_data(user_id: int, user_data: EditUserPersonalData, session: AsyncSession) -> dict[str, Any] | None:
    try:
        user = await get_user_profile_by_id(user_id, session)

        if user:
            if user.is_active:
                if not user_data:
                    return None

                if user_data.name:
                    user.name = user_data.name
                if user_data.phone:
                    user.phone = user_data.phone

                await session.commit()
                await session.refresh(user)
                return user
        return None
    except:
        return None


async def get_company_by_id(company_id, session):
    select_query = select(Company).where(Company.id == company_id).options(selectinload(Company.contacts))
    model = await session.execute(select_query)
    company = model.scalar_one_or_none()
    return company


async def edit_users_company(company_id, company_data, session) -> dict[str, Any] | None:
    try:
        company = await get_company_by_id(company_id, session)

        if company:
            if company_data.name:
                company.name = company_data.name
            if company_data.address:
                company.address = company_data.address
            if company_data.opening_time:
                company.opening_time = company_data.opening_time
            if company_data.closing_time:
                company.closing_time = company_data.closing_time
            if company_data.only_weekdays:
                company.only_weekdays = company_data.only_weekdays

            await session.commit()
            await session.refresh(company)
            return company
        return None
    except:
        return None
