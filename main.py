from fastapi import FastAPI

from database import Base, engine
from routes.auth import router as auth_router
from routes.deploy import router as deploy_router

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="cploy", description="Self-hosted deployment platform")

# Register routers
app.include_router(auth_router)
app.include_router(deploy_router)


@app.get("/")
def health_check():
    return {"status": "working"}