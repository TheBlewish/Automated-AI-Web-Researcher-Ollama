# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install gcc and g++ to prevent llama-cpp-python build error
RUN apt-get update && apt-get install -y gcc g++

# Set the working directory in the container
WORKDIR /app

# Copy the requirements so they only have to be installed once
COPY requirements.txt .

# Install packages
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make port 80 available to the world outside this container
EXPOSE 80

# Run Web-LLM.py when the container launches
CMD ["python", "Web-LLM.py"]
