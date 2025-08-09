from . import config 
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from . import config
from .views.web import router as web_router
from .routers.auth_cognito import router as cognito_router
from .routers.runs import router as runs_router
from .routers.chat import router as chat_router

app = FastAPI(title="FinDocGPT", version="1.0.0")
 
# Static files (CSS, images, JS)
static_path = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Routers
app.include_router(web_router, tags=["web"])
app.include_router(cognito_router, tags=["auth"])
app.include_router(runs_router, tags=["runs"])
app.include_router(chat_router)

from .routers.ai_chat import router as ai_router
app.include_router(ai_router)