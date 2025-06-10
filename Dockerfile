# === 第一阶段：构建依赖 ===
FROM python:3.11-alpine AS builder

# 安装构建依赖
RUN apk add --no-cache \
    build-base \
    cargo \
    gcc \
    libffi-dev \
    musl-dev \
    postgresql-dev

# 设置工作目录
WORKDIR /install

# 复制 requirements 并安装到 /install 目录
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# === 第二阶段：最小运行环境 ===
FROM python:3.11-alpine

# 安装运行时必要库
RUN apk add --no-cache \
    libpq \
    libffi \
    && adduser -D napcat

# 设置工作目录
WORKDIR /app

# 复制安装好的包和应用代码
COPY --from=builder /install /usr/local
COPY . .

# 使用非 root 用户运行
USER napcat

# 设置入口
CMD ["python", "app.py"]
