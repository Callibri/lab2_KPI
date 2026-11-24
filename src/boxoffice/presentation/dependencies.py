from typing import Iterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from boxoffice.application.use_cases import UseCases
from boxoffice.domain.errors import AuthenticationError

bearer_scheme = HTTPBearer(auto_error=False)


def get_use_cases(request: Request) -> Iterator[UseCases]:
    yield from request.app.state.use_case_scope()


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    return request.app.state.tokens.verify(credentials.credentials)
