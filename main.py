from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from roommatch_api.routes import router

app = FastAPI(
    title       = "RoomMatch API",
    description = "Backend API for RoomMatch roommate finder app",
    version     = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = False,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"message": "RoomMatch API is running!"}