# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install gcc and g++ to fix the llama-cpp-python build error
RUN apt-get update && apt-get install -y gcc g++

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run Web-LLM.py when the container launches
CMD ["python", "Web-LLM.py"]
