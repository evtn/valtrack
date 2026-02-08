from contextlib import asynccontextmanager

from fastapi import FastAPI

from tabtrack.database import init_db
from tabtrack.routes import collect, keys, push, sse


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("start init")
    await init_db()
    print("db init complete")
    yield
    print("shutting down")


app = FastAPI(
    title="TimeTracker API",
    lifespan=lifespan,
)

app.include_router(push.router)
app.include_router(collect.router)
app.include_router(keys.keys_router)
app.include_router(keys.admin_router)
app.include_router(sse.router)
