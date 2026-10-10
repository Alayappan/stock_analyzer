# Stage 1: Build Angular 18 application
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency definition
COPY package.json ./

# Install npm dependencies
RUN npm install

# Copy application source code
COPY . .

# Build production bundle
RUN npm run build

# Stage 2: Serve via Nginx
FROM nginx:1.25-alpine

# Copy built artifacts from builder stage (Angular 18 application builder outputs to dist/frontend/browser)
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom Nginx configuration with /api/ reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
