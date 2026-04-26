from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import chat, context, memory, runtime, system, training


app = FastAPI(
    title="CHAPPiE App API",
    version="15.4.2026-api",
    description="FastAPI-Schicht fuer CHAPPiEs React-Frontend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(memory.router)
app.include_router(context.router)
app.include_router(chat.router)
app.include_router(runtime.router)
app.include_router(training.router)
