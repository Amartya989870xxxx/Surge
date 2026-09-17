from fastapi import Request

from app.services import Services


def get_services(request: Request) -> Services:
    return request.app.state.services
