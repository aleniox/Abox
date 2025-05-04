FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Cài Python và các công cụ cần thiết
RUN apt-get update && apt-get install -y python3 python3-pip python3-dev

# Sao chép code và cài đặt gói
WORKDIR /app
COPY . /app
COPY .env .
COPY . .
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

EXPOSE 5000
CMD ["python3", "app.py"]
