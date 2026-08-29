FROM node:24-bookworm-slim AS builder

WORKDIR /app

COPY . ./
RUN npm install

# CMD ["sh", "-c", "${START_COMMAND:-node app.js}"]
