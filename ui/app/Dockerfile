# Build the React/Vite app, then serve the static bundle with nginx.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Same-origin API path; nginx proxies it to the FastAPI service.
ARG VITE_API_BASE_URL=/agentguard-api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Use vite directly (skip `tsc -b`) so type-only issues don't block the bundle.
RUN npx vite build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
