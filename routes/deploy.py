from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import cast

from auth import get_current_user
from database import get_db
from models import Deployment, User
from services.deploy_service import run_deployment

router = APIRouter(prefix="/deploy", tags=["deploy"])


# ── Request / Response Schemas ───────────────────────────────────────────────
class DeployRequest(BaseModel):
    image_name: str
    port: str
    repo_url: str


class DeployResponse(BaseModel):
    deployment_id: int
    status: str
    message: str


class DeployStatusResponse(BaseModel):
    id: int
    image_name: str
    port: str
    repo_url: str
    status: str
    error_message: str | None
    domain: str | None

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────
@router.post("/vite/react", response_model=DeployResponse, status_code=status.HTTP_202_ACCEPTED)
def deploy_vite_react(
    body: DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a Vite+React deployment in the background.
    Returns immediately with a deployment ID that can be polled for status.
    """
    deployment = Deployment(
        user_id=current_user.id,
        image_name=body.image_name,
        port=body.port,
        repo_url=body.repo_url,
        status="pending",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # Fire-and-forget background task
    background_tasks.add_task(
        run_deployment,
        cast(int, deployment.id),
        body.image_name,
        body.port,
        body.repo_url,
    )

    return {
        "deployment_id": deployment.id,
        "status": "pending",
        "message": "Deployment started. Poll /deploy/{id}/status for updates.",
    }


@router.get("/{deployment_id}/status", response_model=DeployStatusResponse)
def get_deployment_status(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check the current status of a deployment."""
    deployment = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.user_id == current_user.id)
        .first()
    )
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    return deployment
