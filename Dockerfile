# Use the official Python image as the base image
FROM python:3.11-slim

# Install the MySQL development libraries and header files
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev gcc

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .


# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port your app runs on
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
