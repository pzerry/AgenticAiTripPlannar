from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from Backend.Exceptions.exception import (
    ActivityAPIError,
    CurrencyAPIError,
    FlightAPIError,
    HotelAPIError,
    WeatherAPIError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(FlightAPIError)
    async def flight_exception_handler(
        request: Request,
        exc: FlightAPIError,
    ):
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(HotelAPIError)
    async def hotel_exception_handler(
        request: Request,
        exc: HotelAPIError,
    ):
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(ActivityAPIError)
    async def activity_exception_handler(
        request: Request,
        exc: ActivityAPIError,
    ):
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(WeatherAPIError)
    async def weather_exception_handler(
        request: Request,
        exc: WeatherAPIError,
    ):
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(CurrencyAPIError)
    async def currency_exception_handler(
        request: Request,
        exc: CurrencyAPIError,
    ):
        return JSONResponse(
            status_code=502,
            content={
                "detail": str(exc),
            },
        )
    