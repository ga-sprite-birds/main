"""System configuration API; mount this router under /fcgi-bin/api."""

from fastapi import APIRouter, Depends

from models.config import ConfigResetRequest, ConfigUpdateRequest
from services.config_service import ConfigError, ConfigService
from system.deps import get_config_service
from system.response import fail, success

router = APIRouter(prefix="/system-config", tags=["system-config"])


@router.get("")
def get_system_config(
    service: ConfigService = Depends(get_config_service),
) -> dict:
    return success({"sections": service.get_schema()})


@router.put("")
def update_system_config(
    request: ConfigUpdateRequest,
    service: ConfigService = Depends(get_config_service),
) -> dict:
    try:
        return success(service.set(request.values))
    except ConfigError as exc:
        return _config_error(exc)


@router.post("/reset")
def reset_system_config(
    request: ConfigResetRequest,
    service: ConfigService = Depends(get_config_service),
) -> dict:
    try:
        if request.all:
            result = service.reset_all()
        elif request.section is not None:
            result = service.reset(request.section)
        else:
            return fail(1001, "section or all is required", {})
        return success(result)
    except ConfigError as exc:
        return _config_error(exc)


def _config_error(exc: ConfigError) -> dict:
    data = dict(exc.details)
    if exc.key is not None:
        data["key"] = exc.key
    return fail(exc.code, exc.msg, data)
