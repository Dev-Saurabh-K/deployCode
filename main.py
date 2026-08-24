from fastapi import FastAPI
import subprocess

app = FastAPI()

@app.get("/")
def test():
    return({
        "status":"working"
    })

@app.post("/run")
def run_command():
    result = subprocess.run(
        ["python", "--version"],
        capture_output=True,
        text=True
    )

    return {
        "output": result.stdout,
        "error": result.stderr,
        "return_code": result.returncode
    }
@app.get("/deploy/vite/react")
def deploy_vite_react(image_name:str, port:str, repo_url:str):

    # image_name = "app5"
    # port = "10005"
    # repo_url = "https://github.com/username/repository.git"

    
    result = subprocess.run(
        [
            "/bin/bash",
            "/home/saurabh/deployCode/scripts/create_deployment_dir.sh",
            image_name
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "step": "create_deployment",
            "success": False,
            "error": result.stderr
        }

    result = subprocess.run(
        [
            "/bin/bash",
            "/home/saurabh/deployCode/scripts/create_compose.sh",
            image_name,
            port
        ],
        capture_output=True,
        text=True
    )
   
    if result.returncode != 0:
        return {
            "step": "create_compose",
            "success": False,
            "error": result.stderr
        }
    
    result = subprocess.run(
        [
            "/bin/bash",
            "/home/saurabh/deployCode/scripts/clone_git_repo.sh",
            image_name,
            repo_url
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "step": "git_setup",
            "success": False,
            "error": result.stderr
        }


    
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=f"/opt/deployCode/{image_name}",
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "step": "docker_compose",
            "success": False,
            "error": result.stderr
        }

   
    result = subprocess.run(
        [
            "sudo",
            "/home/saurabh/deployCode/scripts/setup_nginx.sh",
            image_name,
            port
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "step": "nginx",
            "success": False,
            "error": result.stderr
        }

    return {
        "success": True,
        "image_name": image_name,
        "port": port,
        "domain": f"{image_name}.dev-saurabh-k.xyz"
    }