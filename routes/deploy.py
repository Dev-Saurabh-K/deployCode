from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import re

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import cast

from auth import get_current_user
from database import get_db
from models import Deployment, User
from services.deploy_service import run_deployment, run_delete_deployment

router = APIRouter(prefix="/deploy", tags=["deploy"])


# ── Request / Response Schemas ───────────────────────────────────────────────
class DeployRequest(BaseModel):
    image_name: str = Field(min_length=1, max_length=63)
    repo_url: str
    environment_variables: dict[str, str] = Field(default_factory=dict)

    @field_validator("image_name")
    @classmethod
    def validate_image_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", value):
            raise ValueError(
                "App name must be 1-63 lowercase letters, digits, or internal hyphens, and start with a letter"
            )
        return value

    @field_validator("environment_variables")
    @classmethod
    def validate_environment_variables(cls, values: dict[str, str]) -> dict[str, str]:
        if len(values) > 100:
            raise ValueError("A maximum of 100 environment variables is allowed")

        for key, value in values.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError(f"Invalid environment variable name: {key}")
            if "\n" in value or "\r" in value or "\x00" in value:
                raise ValueError("Environment variable values cannot contain newlines or null bytes")

        return values


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

MAX_DEPLOYMENTS_PER_USER = 2
PORT_RANGE_START = 10000
PORT_RANGE_END = 40000


def _next_available_port(db: Session) -> str:
    """Find the next unused port in the range 10000–40000."""
    used_ports = {
        int(row[0])
        for row in db.query(Deployment.port)
        .filter(Deployment.status.notin_(["deleted", "failed"]))
        .all()
    }
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port not in used_ports:
            return str(port)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No available ports. Please try again later.",
    )


# ── Routes ───────────────────────────────────────────────────────────────────
@router.get("/my-projects", response_model=list[DeployStatusResponse])
def list_my_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all deployments belonging to the authenticated user."""
    deployments = (
        db.query(Deployment)
        .filter(Deployment.user_id == current_user.id)
        .order_by(Deployment.created_at.desc())
        .all()
    )
    return deployments


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
    # Enforce per-user deployment limit
    active_count = (
        db.query(Deployment)
        .filter(
            Deployment.user_id == current_user.id,
            Deployment.status.notin_(["deleted", "failed"]),
        )
        .count()
    )
    if active_count >= MAX_DEPLOYMENTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Deployment limit reached. Maximum {MAX_DEPLOYMENTS_PER_USER} active deployments per user.",
        )

    # App names become Docker container names and subdomains, so they must be
    # unique across every active deployment, not just this user's deployments.
    existing_app = (
        db.query(Deployment.id)
        .filter(
            func.lower(Deployment.image_name) == body.image_name,
            Deployment.status.notin_(["deleted", "failed"]),
        )
        .first()
    )
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active deployment already uses this app name.",
        )

    # Auto-assign a unique port
    assigned_port = _next_available_port(db)

    deployment = Deployment(
        user_id=current_user.id,
        image_name=body.image_name,
        port=assigned_port,
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
        assigned_port,
        body.repo_url,
        body.environment_variables,
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


@router.delete("/{deployment_id}", response_model=DeployResponse)
def delete_deployment(
    deployment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a deployment — tears down Docker container, nginx config, and files."""
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

    if deployment.status == "deleting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deployment is already being deleted",
        )

    if deployment.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Deployment has already been deleted",
        )

    background_tasks.add_task(
        run_delete_deployment,
        deployment_id,
        deployment.image_name,
    )

    return {
        "deployment_id": deployment_id,
        "status": "deleting",
        "message": "Deletion started. Poll /deploy/{id}/status for updates.",
    }
