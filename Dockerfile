FROM python:3.12-slim

WORKDIR /app

# Cài đặt dependencies hệ thống (nếu cần)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các package Python (thêm requests + version ổn định)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        fastapi==0.115.2 \
        uvicorn[standard]==0.30.6 \
        python-dotenv==1.0.1 \
        requests==2.32.3

# Copy code vào container
COPY . .

# Tạo user không root (giữ an toàn)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# SỬA QUAN TRỌNG: Dùng "app:app" vì file của bạn là app.py
# Bỏ --reload khi chạy production (nếu muốn dev thì giữ)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]