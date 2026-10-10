from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.routes import auth, root
from src.schemas.response import ApiResponse

app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(str(exc.detail)).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            ApiResponse[list[dict[str, object]]].fail(
                "Validation error", data=errors
            )
        ),
    )


app.include_router(root.router)
app.include_router(auth.router)
