# Sử dụng Python 3.12 làm image cơ sở
FROM python:3.12.13

RUN apt-get update && apt-get install -y \
    # python3 \
    # python3-venv \
    # python3-pip (thay bằng uv - nhanh hơn) \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy file requirements.txt vào container
COPY requirements.txt /app/

# Tạo venv
# RUN python3 -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# Cài đặt uv binary trực tiếp (nhanh hơn pip)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
COPY . /app/

# Cài đặt các thư viện từ requirements.txt
RUN uv sync

# Cài đặt Playwright browser (chromium) và các dependencies hệ thống cần thiết
# RUN playwright install chromium
# RUN playwright install-deps chromium
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# Copy toàn bộ mã nguồn vào container

EXPOSE 5000
CMD ["uv", "run", "main.py"]
