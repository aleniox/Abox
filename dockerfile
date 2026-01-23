# Sử dụng Python 3.12 làm image cơ sở
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    # python3-pip (thay bằng uv - nhanh hơn) \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy file requirements.txt vào container
COPY requirements.txt /app/

# Tạo venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Cài đặt uv binary trực tiếp (nhanh hơn pip)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Cài đặt các thư viện từ requirements.txt (dùng PyPI mirror Aliyun)
RUN uv pip install \
    --index-url https://mirrors.aliyun.com/pypi/simple \
    --extra-index-url https://pypi.org/simple \
    --no-cache-dir \
    -r requirements.txt

# Copy toàn bộ mã nguồn vào container (TRƯỚC khi install Chrome)
COPY . /app/

# Cài đặt Chrome từ file deb có sẵn
RUN apt-get update && apt-get install -y /app/data/google-chrome-stable_current_amd64.deb && rm -rf /var/lib/apt/lists/*

EXPOSE 5000
CMD ["python3", "main.py"]
