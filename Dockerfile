# Use the official Python image as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /api

# Copy the application code into the container
COPY /api /api

# Install Python dependencies
RUN pip install -r /api/requirements.txt

# Set environment variables
ENV DB_USER=add_your_user_here
ENV DB_PASSWORD=add_your_password_here
ENV DB_HOST=add_your_host_here
ENV DB_PORT=add_your_port_here
ENV DB_NAME=add_schema_here

# Run the application
CMD ["python", "/api/app.py"]
