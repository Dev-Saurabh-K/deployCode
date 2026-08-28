from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_admin, hash_password
from database import get_db
from models import Deployment, User
from services.deploy_service import run_delete_deployment

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
    deployment_count: int


class AdminDeploymentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    image_name: str
    port: str
    repo_url: str
    status: str
    error_message: str | None
    domain: str | None
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    is_admin: bool | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Username cannot be blank")
        return value


def _admin_deployment_response(deployment: Deployment, username: str) -> dict:
    return {
        "id": deployment.id,
        "user_id": deployment.user_id,
        "username": username,
        "image_name": deployment.image_name,
        "port": deployment.port,
        "repo_url": deployment.repo_url,
        "status": deployment.status,
        "error_message": deployment.error_message,
        "domain": deployment.domain,
        "created_at": deployment.created_at,
        "updated_at": deployment.updated_at,
    }


@router.get("/deployments", response_model=list[AdminDeploymentResponse])
def list_all_deployments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """List every deployment and its owner."""
    rows = (
        db.query(Deployment, User.username)
        .join(User, Deployment.user_id == User.id)
        .order_by(Deployment.created_at.desc())
        .all()
    )
    return [_admin_deployment_response(deployment, username) for deployment, username in rows]


@router.delete("/deployments/{deployment_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_any_deployment(
    deployment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Start deletion of any user's deployment."""
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
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

    deployment.status = "deleting"
    db.commit()
    background_tasks.add_task(run_delete_deployment, deployment.id, deployment.image_name)
    return {
        "deployment_id": deployment.id,
        "status": "deleting",
        "message": "Deletion started.",
    }


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """List all users with their deployment counts."""
    rows = (
        db.query(User, func.count(Deployment.id).label("deployment_count"))
        .outerjoin(Deployment, Deployment.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "deployment_count": deployment_count,
        }
        for user, deployment_count in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Update a user's name, password, or administrator role."""
    if not body.model_fields_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes supplied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.username is not None and body.username != user.username:
        existing = db.query(User.id).filter(User.username == body.username).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
        user.username = body.username

    if body.password is not None:
        user.hashed_password = hash_password(body.password)

    if "is_admin" in body.model_fields_set and body.is_admin != user.is_admin:
        if user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot change their own administrator role",
            )
        if not body.is_admin:
            admin_count = db.query(User).filter(User.is_admin.is_(True)).count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="At least one administrator must remain",
                )
        user.is_admin = body.is_admin

    db.commit()
    db.refresh(user)
    deployment_count = db.query(Deployment).filter(Deployment.user_id == user.id).count()
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "deployment_count": deployment_count,
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Response:
    """Delete a user after all of their active deployments have been removed."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators cannot delete their own account",
        )

    active_deployments = (
        db.query(Deployment)
        .filter(
            Deployment.user_id == user.id,
            Deployment.status.notin_(["deleted", "failed"]),
        )
        .count()
    )
    if active_deployments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete the user's active deployments before deleting the user",
        )

    if user.is_admin and db.query(User).filter(User.is_admin.is_(True)).count() <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="At least one administrator must remain",
        )

    db.query(Deployment).filter(Deployment.user_id == user.id).delete()
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
