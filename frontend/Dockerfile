# Use a more recent Node.js version for building the frontend
FROM node:18-alpine as build
# Set the working directory inside the container
WORKDIR /app
# Copy package.json and package-lock.json
COPY package.json package-lock.json ./
# Install dependencies
RUN npm ci
# Copy the rest of the application's source code
COPY . .
# Build the static files for production
# The ARG is used to pass build-time variables
ARG VITE_REACT_APP_BACKEND_URL
ENV VITE_REACT_APP_BACKEND_URL=$VITE_REACT_APP_BACKEND_URL
RUN npm run build

# Use a lightweight web server for serving the static files
FROM nginx:alpine
# Remove default nginx static assets and config
RUN rm -rf /usr/share/nginx/html/* && \
    rm -f /etc/nginx/conf.d/default.conf

# Add MIME types configuration
RUN echo 'types { \
    application/javascript mjs; \
    application/javascript js; \
    application/javascript module; \
    text/javascript mjs; \
    text/javascript js; \
    text/javascript module; \
}' > /etc/nginx/conf.d/custom-mime.types

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built files from the previous stage to nginx's static directory
COPY --from=build /app/dist /usr/share/nginx/html

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    ls -la /usr/share/nginx/html

# Expose port 80 for web traffic
EXPOSE 80

# Start nginx server
CMD ["nginx", "-g", "daemon off;"]
