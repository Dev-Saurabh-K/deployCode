import subprocess
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Deployment


def run_deployment(
    deployment_id: int,
    image_name: str,
    port: str,
    repo_url: str,
    environment_variables: dict[str, str],
):
    """
    Execute the full deployment pipeline in a background task.
    Uses its own DB session since BackgroundTasks run outside the request lifecycle.
    """
    db: Session = SessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            return

        # Mark as running
        deployment.status = "running"
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Step 1: Create deployment directory
        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/create_deployment_dir.sh",
                image_name,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"create_deployment: {result.stderr}")
            return

        # Step 2: Create docker-compose file
        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/create_compose.sh",
                image_name,
                port,
                *[f"{key}={value}" for key, value in environment_variables.items()],
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"create_compose: {result.stderr}")
            return

        # Step 3: Clone git repository
        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/clone_git_repo.sh",
                image_name,
                repo_url,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"git_setup: {result.stderr}")
            return

        # Step 4: Docker compose up
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=f"/opt/deployCode/{image_name}",
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"docker_compose: {result.stderr}")
            return

        # Step 5: Setup nginx
        result = subprocess.run(
            [
                "sudo",
                "/home/saurabh/deployCode/scripts/setup_nginx.sh",
                image_name,
                port,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"nginx: {result.stderr}")
            return

        # All steps passed — mark success
        deployment.status = "success"
        deployment.domain = f"{image_name}.dev-saurabh-k.xyz"
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        _fail(db, deployment, f"unexpected_error: {str(exc)}")
    finally:
        db.close()


def run_node_deployment(
    deployment_id: int,
    image_name: str,
    port: str,
    repo_url: str,
    environment_variables: dict[str, str],
):
    """
    Execute the Node.js deployment pipeline using the dedicated Node scripts.
    """
    db: Session = SessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            return

        deployment.status = "running"
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/create_node_dir.sh",
                image_name,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"create_node_deployment: {result.stderr}")
            return

        node_start_command = environment_variables.get("START_COMMAND", "node app.js")
        env_without_start = {
            key: value for key, value in environment_variables.items() if key != "START_COMMAND"
        }

        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/create_node_compose.sh",
                image_name,
                port,
                "3000",
                node_start_command,
                *[f"{key}={value}" for key, value in env_without_start.items()],
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"create_node_compose: {result.stderr}")
            return

        result = subprocess.run(
            [
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/clone_git_repo.sh",
                image_name,
                repo_url,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"git_setup: {result.stderr}")
            return

        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=f"/opt/deployCode/{image_name}",
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"docker_compose: {result.stderr}")
            return

        result = subprocess.run(
            [
                "sudo",
                "/home/saurabh/deployCode/scripts/setup_nginx.sh",
                image_name,
                port,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(db, deployment, f"nginx: {result.stderr}")
            return

        deployment.status = "success"
        deployment.domain = f"{image_name}.dev-saurabh-k.xyz"
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        _fail(db, deployment, f"unexpected_error: {str(exc)}")
    finally:
        db.close()


def _fail(db: Session, deployment: Deployment, error_msg: str):
    """Mark a deployment as failed and persist the error."""
    deployment.status = "failed"
    deployment.error_message = error_msg
    deployment.updated_at = datetime.now(timezone.utc)
    db.commit()


def run_delete_deployment(deployment_id: int, image_name: str):
    """
    Execute the delete_deployment.sh script in a background task.
    Uses its own DB session since BackgroundTasks run outside the request lifecycle.
    """
    db: Session = SessionLocal()
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            return

        deployment.status = "deleting"
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

        result = subprocess.run(
            [
                "sudo",
                "/bin/bash",
                "/home/saurabh/deployCode/scripts/delete_deployment.sh",
                image_name,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            _fail(db, deployment, f"delete: {result.stderr}")
            return

        deployment.status = "deleted"
        deployment.domain = None
        deployment.updated_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        _fail(db, deployment, f"delete_error: {str(exc)}")
    finally:
        db.close()
