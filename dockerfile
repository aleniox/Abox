# Sử dụng Python 3.12.3 làm image cơ sở
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu24.04

# Thiết lập biến môi trường để đảm bảo Python ghi log ra ngay lập tức

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    tesseract-ocr \
    tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*
# Thiết lập thư mục làm việc trong container
WORKDIR /app

# RUN pip install uv
# Copy file requirements.txt vào container
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y python3-venv

# Tạo venv
RUN python3 -m venv /opt/venv

# Dùng pip trong venv
ENV PATH="/opt/venv/bin:$PATH"
# RUN pip install --no-cache-dir -r requirements.txt
# Cài đặt các thư viện yêu cầu từ requirements.txt
RUN pip install -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . /app/

EXPOSE 5000
CMD ["python3", "main.py"]
