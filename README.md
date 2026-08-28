# cploy

**cploy** is a self-hosted platform for building and publishing Vite + React
applications from Git repositories. It prepares an isolated deployment
directory, builds the application in Docker, serves the static result with an
Nginx container, and places an Nginx reverse proxy in front of the container.

This README covers the project, local development, deployment host setup, and
operations.

## What cploy does

- Authenticates users and keeps deployment records in SQLite.
- Allocates an available host port for every active deployment.
- Validates app names before deployment work begins.
- Clones a repository's `main` branch into a dedicated deployment directory.
- Builds the Vite application in a multi-stage Docker image.
- Serves the built static files from Nginx inside a container.
- Creates a host-level Nginx reverse-proxy configuration for the app subdomain.
- Supports per-deployment environment variables through a generated `.env` file.
- Removes the container, proxy configuration, and deployment files when a
  deployment is deleted.

## Architecture

```text
Browser
  │
  ▼
Host Nginx ──► app-name.dev-saurabh-k.xyz
  │                         │
  │                         ▼
  │                    Docker container
  │                         │
  │                         ▼
  │                  Nginx (static Vite build)
  │
  ▼
cploy service ──► SQLite deployment records
       │
       ├──► Git repository checkout
       ├──► Docker Compose build and startup
       └──► Host Nginx configuration
```

## Repository layout

| Path | Purpose |
|---|---|
| `main.py` | Application entry point and CORS configuration. |
| `auth.py` | Password hashing and token authentication configuration. |
| `models.py` | SQLite data models for users and deployments. |
| `routes/` | Application request handling. |
| `services/deploy_service.py` | Background deployment and deletion orchestration. |
| `scripts/` | Linux deployment, Docker Compose, repository, and Nginx automation. |
| `templates/Dockerfile` | Universal multi-stage Docker build for deployed Vite apps. |
| `templates/nginx.conf` | Nginx configuration installed inside each application container. |
| `sample/` | Example Vite + React applications. |

## Prerequisites

### Local development

- Python 3.10 or later
- `pip`
- Git

### Deployment host

- Linux host with Bash
- Docker Engine with the Docker Compose plugin (`docker compose`)
- Git
- Nginx installed and enabled
- A DNS wildcard or individual DNS records pointing app subdomains to the host
- Permission for the service user to manage Docker and reload Nginx
- A directory in which deployments can be created (the current scripts use
  `/opt/deployCode`)

## Local setup

1. Clone the repository and enter it.

   ```bash
   git clone <your-repository-url>
   cd cploy
   ```

2. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   ```

   On macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Start the service for local development.

   ```bash
   uvicorn main:app --reload
   ```

SQLite creates `cploy.db` automatically in the working directory. It is
ignored by Git so local data is not committed.

## Preparing a deployment host

The scripts are designed to run on the Linux deployment host. Review and adapt
the paths and domain before using them outside the current environment.

### 1. Place the project on the host

The scripts currently reference the project templates at:

```text
/home/saurabh/deployCode/templates
```

and create deployed applications at:

```text
/opt/deployCode/<app-name>
```

If your checkout lives elsewhere, update the absolute template paths in
`scripts/create_deployment_dir.sh` and the script paths in
`services/deploy_service.py` together.

### 2. Configure the domain

The host Nginx script currently creates sites for:

```text
<app-name>.dev-saurabh-k.xyz
```

Change this domain in both `scripts/setup_nginx.sh` and
`services/deploy_service.py` if you use another domain. Ensure the matching DNS
record resolves to the deployment host.

### 3. Grant only the required permissions

The service account needs permission to:

- Run Docker and Docker Compose.
- Write deployment directories under `/opt/deployCode`.
- Create and enable Nginx site configurations.
- Test and reload Nginx.

Use narrowly scoped `sudoers` rules when the application runs under a service
account. Do not grant unrestricted root access merely to run deployments.

### 4. Protect application secrets

Before production use, replace the hard-coded token signing key in `auth.py`
with a securely managed environment variable. Keep the production database,
deployment `.env` files, and generated Nginx configurations readable only by
the appropriate host users.

## Deployment workflow

Each deployment is processed in the background and follows this sequence:

1. Validate the app name and confirm no active deployment already uses it.
2. Reserve an available port.
3. Create `/opt/deployCode/<app-name>`.
4. Copy the universal `Dockerfile` and container Nginx configuration into that
   directory.
5. Generate `.env` and `docker-compose.yml`.
6. Initialize the deployment directory as a Git checkout and pull the
   repository's `main` branch.
7. Run `docker compose up -d --build` in the deployment directory.
8. Configure the host Nginx reverse proxy and reload Nginx.

If a step fails, the deployment record is marked as failed and includes an
error message for troubleshooting.

## App-name rules

An app name is used as the deployment directory name, Docker container name,
and subdomain. Names must therefore be:

- 1 to 63 characters long
- Lowercase
- Started with a letter
- Made from lowercase letters, digits, and internal hyphens only
- Unique among active deployments, including deployments owned by other users

Examples: `portfolio`, `shop2`, and `my-app` are valid. `MyApp`, `my_app`,
`-app`, and `app-` are not valid.

## Environment variables

Deployment-specific variables are passed to the deployment workflow and
written to:

```text
/opt/deployCode/<app-name>/.env
```

The generated Compose file references this file with `env_file: .env`, making
the variables available to the running container. Variable names must start
with a letter or underscore and may contain only letters, digits, and
underscores. Values cannot contain line breaks. A maximum of 100 variables is
allowed for one deployment.

### Important: Vite build-time variables

Vite replaces `VITE_*` values while `npm run build` is running. The generated
Compose `.env` file is loaded when the finished Nginx container starts, so it
does not by itself change values already bundled into a static Vite build. Use
build arguments and matching Dockerfile `ARG`/`ENV` instructions if a deployed
Vite application needs configuration embedded at build time.

## Docker and Nginx configuration

### Application container

`templates/Dockerfile` uses two stages:

1. A Node image installs dependencies and runs the Vite build.
2. An `nginx:alpine` image serves the resulting `dist` directory.

The deployment setup copies `templates/nginx.conf` beside the Dockerfile. The
Dockerfile installs it as:

```text
/etc/nginx/conf.d/default.conf
```

That configuration provides SPA fallback (`/index.html`) so client-side routes
continue to work when loaded directly.

### Host reverse proxy

`scripts/setup_nginx.sh` creates a server block under
`/etc/nginx/sites-available`, enables it with a symlink in
`/etc/nginx/sites-enabled`, tests the Nginx configuration, then reloads Nginx.
The proxy forwards the app subdomain to the port allocated to its Docker
container.

## Operations and troubleshooting

### View a deployment directory

On the deployment host, inspect the application files, generated Compose
configuration, and `.env` file at:

```text
/opt/deployCode/<app-name>
```

### Inspect containers

From that deployment directory:

```bash
docker compose ps
docker compose logs
```

### Rebuild an application

From the same directory:

```bash
docker compose up -d --build
```

### Check host Nginx

```bash
sudo nginx -t
sudo systemctl status nginx
```

### Common issues

| Symptom | Likely cause | Suggested check |
|---|---|---|
| Container fails to build | Repository is not a compatible Vite project or dependencies fail to install | Inspect `docker compose logs` and the repository's `package.json`. |
| App subdomain does not resolve | DNS record is missing or points to the wrong host | Verify DNS and the configured base domain. |
| Nginx fails to reload | Invalid generated or existing Nginx configuration | Run `sudo nginx -t` and inspect the named site file. |
| Compose cannot start | Docker is unavailable or the assigned port is occupied outside cploy | Check Docker service status and host port usage. |
| Environment variable is unavailable in the browser | Static Vite values are fixed at build time | Use build-time configuration rather than only Compose runtime variables. |

## Sample applications

The `sample/` directory contains small Vite + React projects for testing the
container build. They are useful for verifying a deployment host before using a
production repository.

## Project status

cploy is tailored to its current self-hosted deployment environment. Before
exposing it publicly, review authentication secret management, host permissions,
rate limiting, logging, database backups, and deployment isolation for your own
security and reliability requirements.
