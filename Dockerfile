# syntax=docker/dockerfile:1
FROM python:3-alpine
WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
COPY . .
CMD ["python3", "main.py", "--base-dir", "/mediathek"]
