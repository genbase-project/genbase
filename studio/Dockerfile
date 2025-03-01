FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set build arguments for environment variables
ARG VITE_ENGINE_URL
ARG VITE_API_USERNAME
ARG VITE_API_PASSWORD

# Set environment variables for build
ENV VITE_ENGINE_URL=${VITE_ENGINE_URL}
ENV VITE_API_USERNAME=${VITE_API_USERNAME}
ENV VITE_API_PASSWORD=${VITE_API_PASSWORD}

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 5173

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]