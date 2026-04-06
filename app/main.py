from datetime import timedelta
from typing import Dict

from fastapi import FastAPI, Depends, HTTPException, status

from app.auth import (
    User,
    UserLogin,
    Token,
    TokenData,
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    verify_api_key,
    require_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

app = FastAPI(
    title="DevTool Authentication API",
    version="1.0.0",
    description="JWT-based authentication with role-based access control",
)

users_db: Dict[str, User] = {}
user_id_counter = 1


@app.post("/auth/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def register(username: str, email: str, password: str) -> Dict[str, str]:
    global user_id_counter
    if username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    hashed_password = get_password_hash(password)
    user = User(
        id=user_id_counter,
        email=email,
        username=username,
        hashed_password=hashed_password,
        roles=["user"],
    )
    users_db[username] = user
    user_id_counter += 1
    return {"message": "User registered successfully", "username": username}


@app.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin) -> Token:
    user = users_db.get(user_login.username)
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/auth/logout", response_model=Dict[str, str])
async def logout(current_user: TokenData = Depends(get_current_user)) -> Dict[str, str]:
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=Dict[str, str])
async def get_me(current_user: TokenData = Depends(get_current_user)) -> Dict[str, str]:
    return {"username": current_user.username, "roles": ",".join(current_user.roles)}


@app.get("/admin/users", response_model=Dict[str, int])
async def list_users(current_user: TokenData = Depends(require_admin)) -> Dict[str, int]:
    return {"total_users": len(users_db)}


@app.post("/service/health", response_model=Dict[str, str])
async def service_health(api_key_valid: bool = Depends(verify_api_key)) -> Dict[str, str]:
    return {"status": "healthy", "service": "authentication"}


@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    return {"message": "DevTool Authentication API", "version": "1.0.0"}
