FROM node:18-alpine
WORKDIR /app

# Copy everything
COPY . .

# Install dependencies and build
RUN npm install
RUN npm run build

# Set environment and port
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000
CMD ["npm", "start"]