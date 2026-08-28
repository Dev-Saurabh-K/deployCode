FROM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package*.json ./

# Try strict lockfile install first; fall back gracefully to legacy peer deps if conflicts exist
RUN npm ci || npm install --legacy-peer-deps

COPY . .
RUN npm run build
RUN if [ -d "/app/build" ] && [ ! -d "/app/dist" ]; then mv /app/build /app/dist; fi

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
