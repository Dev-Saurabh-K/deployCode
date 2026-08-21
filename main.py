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