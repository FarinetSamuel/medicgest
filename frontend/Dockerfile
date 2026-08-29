# --- Étape 1 : build ---
FROM node:22-slim AS build
WORKDIR /app

# L'URL de l'API est figée au moment du build (Vite intègre les variables
# VITE_* dans le bundle statique, elles ne sont pas lues à l'exécution).
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Étape 2 : service statique ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
