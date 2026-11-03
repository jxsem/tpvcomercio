from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routes.auth import router as auth_router
from backend.routes.category import router as category_router
from backend.routes.product import router as product_router
from backend.routes.return_ import router as return_router
from backend.routes.sale import router as sale_router
from backend.routes.user import router as user_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(sale_router)
app.include_router(return_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
