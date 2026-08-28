from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import bootstrap_admin_from_environment
from database import Base, engine, upgrade_schema
from routes.admin import router as admin_router
from routes.auth import router as auth_router
from routes.deploy import router as deploy_router

# Create all database tables on startup
Base.metadata.create_all(bind=engine)
upgrade_schema()
bootstrap_admin_from_environment()

app = FastAPI(title="cploy", description="Self-hosted deployment platform")

# CORS — allowed origins
origins = [
    "http://localhost:5173",
    "https://dev-saurabh-k.xyz",
    "https://www.dev-saurabh-k.xyz",
    "https://cploy.dev-saurabh-k.xyz",
    "https://deploycode-chi.vercel.app",
    "https://deploycode-git-main-saurabh-kumars-projects-ee8f1350.vercel.app",
    "https://deploycode.dev-saurabh-k.xyz"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(deploy_router)
app.include_router(admin_router)


@app.get("/")
def health_check():
    return {"status": "working"}
