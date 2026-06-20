# ── Build stage ────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --silent

COPY . .

# Variables d'environnement injectées au build
ARG VITE_API_BASE_URL=https://api.coderoute.gov.gn
ARG VITE_API_URL=https://api.coderoute.gov.gn/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Serve stage ────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS serve

# Configuration Nginx pour SPA (React Router hash-based)
RUN cat > /etc/nginx/conf.d/default.conf << 'NGINX'
server {
    listen 4173;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Cache long pour les assets hashés
    location ~* \.(js|css|png|svg|ico|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback — toutes les routes → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /ping {
        return 200 "ok";
        add_header Content-Type text/plain;
    }
}
NGINX

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 4173
CMD ["nginx", "-g", "daemon off;"]
