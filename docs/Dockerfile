FROM node:22-alpine

# Set working directory
WORKDIR /app

# Copy everything except .next, .source folders and node_modules
COPY . .

# Install dependencies
RUN npm ci

# Build the application
RUN npm run build

# Expose the port the app will run on
EXPOSE 3000

# Start the application
CMD ["npm", "start"]