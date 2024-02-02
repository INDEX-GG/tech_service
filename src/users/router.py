from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from src.auth import service as auth_service
from src.auth.exceptions import UsernameTaken, InvalidCredentials
from src.users import service as users_service
from src.auth.jwt import validate_admin_access, parse_jwt_user_data, validate_users_access
from src.auth.schemas import JWTData
from src.database import get_async_session
from src.users.schemas import UserResponse, CustomerUserResponse, ExecutorUserResponse, CustomersListPaginated, \
    ExecutorsListPaginated, CreateExecutorInput, CreateCustomerInput, EditUserCredentials, EditUserPersonalData

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_account(
    jwt_data: JWTData = Depends(parse_jwt_user_data),
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    user = await users_service.get_user_profile_by_id(jwt_data.user_id, session)

    return user


@router.get("/customer/{user_id}", response_model=CustomerUserResponse, dependencies=[Depends(validate_admin_access)])
async def get_customer_account(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    role = "is_customer"
    user = await users_service.get_user_by_role(user_id, role, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")


@router.get("/executor/{user_id}", response_model=ExecutorUserResponse, dependencies=[Depends(validate_admin_access)])
async def get_executor_account(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    role = "is_executor"
    user = await users_service.get_user_by_role(user_id, role, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")


@router.get("/customers/all", response_model=CustomersListPaginated, dependencies=[Depends(validate_admin_access)])
async def get_customers_list(
    search: str = Query(None, min_length=2),
    page: int = 1,
    limit: int = Query(default=25, lte=50),
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    offset = (page - 1) * limit
    response = await users_service.get_customers(search, offset, limit, session)

    return response


@router.get("/executors/all", response_model=ExecutorsListPaginated, dependencies=[Depends(validate_admin_access)])
async def get_executors_list(
    search: str = Query(None, min_length=2),
    page: int = 1,
    limit: int = Query(default=25, lte=50),
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    offset = (page - 1) * limit
    response = await users_service.get_executors(search, offset, limit, session)

    return response


@router.post("/customers/create", status_code=status.HTTP_201_CREATED, response_model=CustomerUserResponse, dependencies=[Depends(validate_admin_access)])
async def create_new_customer(
    customer_data: CreateCustomerInput,
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    customer = await users_service.create_customer(customer_data, session)

    if customer:
        role = "is_customer"
        user = await users_service.get_user_by_role(customer.id, role, session)
        if user:
            return user
        else:
            raise HTTPException(status_code=400, detail="Ошибка при формировании ответа")


@router.post("/executors/create", status_code=status.HTTP_201_CREATED, response_model=ExecutorUserResponse, dependencies=[Depends(validate_admin_access)])
async def create_new_executor(
    executor_data: CreateExecutorInput,
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    response = await users_service.create_executor(executor_data, session)
    return response


@router.delete("/block/{user_id}", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(validate_admin_access)])
async def block_user_account(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> JSONResponse:

    result = await users_service.block_user(user_id, session)
    if result:
        return JSONResponse(content={"message": "Пользователь успешно удален(заблокирован)"})
    else:
        raise HTTPException(status_code=404, detail="Пользователь не найден")


@router.patch("/credentials/{user_id}", response_model=UserResponse, dependencies=[Depends(validate_admin_access)])
async def edit_users_credentials_by_admin(
        user_id: int,
        user_data: EditUserCredentials,
        session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    if user_data.username:
        user = await auth_service.get_user_by_username(user_data.username)
        if user:
            raise UsernameTaken()

    user = await users_service.edit_credentials(user_id, user_data, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")


@router.patch("/personal_data/{user_id}", response_model=UserResponse, dependencies=[Depends(validate_admin_access)])
async def edit_users_personal_data_by_admin(
        user_id: int,
        user_data: EditUserPersonalData,
        session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    user = await users_service.edit_personal_data(user_id, user_data, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")


@router.patch("/me/credentials", response_model=UserResponse)
async def edit_my_credentials(
    user_data: EditUserCredentials,
    jwt_data: JWTData = Depends(parse_jwt_user_data),
    session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    if user_data.username:
        user = await auth_service.get_user_by_username(user_data.username)
        if user:
            raise UsernameTaken()

    user = await users_service.edit_credentials(jwt_data.user_id, user_data, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")


@router.patch("/me/personal_data", response_model=UserResponse)
async def edit_my_personal_data(
        user_data: EditUserPersonalData,
        jwt_data: JWTData = Depends(parse_jwt_user_data),
        session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    user = await users_service.edit_personal_data(jwt_data.user_id, user_data, session)

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="Пользователь на найден")




# @router.patch("/executor/{user_id}", response_model=ExecutorUserResponse, dependencies=[Depends(validate_admin_access)])
# async def edit_executor_credentials(
#         user_id: int,
#         executor_data: EditUserCredentials,
#         session: AsyncSession = Depends(get_async_session)
# ) -> dict[str, Any]:
#     role = "is_executor"
#     user = await users_service.get_user_by_role(user_id, role, session)
#
#     if user:
#         if executor_data.username:
#             user.username = executor_data.username
#         if executor_data.password:
#             user.password = executor_data.password
#         await session.commit()
#         await session.refresh(user)
#         return user
#     else:
#         raise HTTPException(status_code=404, detail="Пользователь на найден")


# @router.patch("/customer/{user_id}", response_model=CustomerUserResponse, dependencies=[Depends(validate_admin_access)])
# async def edit_customer_account(
#     user_id: int,
#     customer_data: CreateCustomerInput,
#     session: AsyncSession = Depends(get_async_session)
# ) -> dict[str, Any]:
#     role = "is_customer"
#     user = await users_service.get_user_by_role(user_id, role, session)
#
#     if user:
#         # user
#
#
#         return user
#     else:
#         raise HTTPException(status_code=404, detail="Пользователь на найден")


# @router.get("/executor/{user_id}", response_model=ExecutorUserResponse, dependencies=[Depends(validate_admin_access)])
# async def get_executor_account(
#     user_id: int,
#     session: AsyncSession = Depends(get_async_session)
# ) -> dict[str, Any]:
#     role = "is_executor"
#     user = await users_service.get_user_by_role(user_id, role, session)
#
#     if user:
#         return user
#     else:
#         raise HTTPException(status_code=404, detail="Пользователь на найден")
