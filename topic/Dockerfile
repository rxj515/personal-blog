FROM python:3.9-slim

WORKDIR /app

# 设置中文环境变量
ENV LANG=zh_CN.UTF-8
ENV LANGUAGE=zh_CN:zh
ENV LC_ALL=zh_CN.UTF-8

# Debian APT 源切换为阿里云
RUN sed -i \
    -e 's|deb.debian.org|mirrors.aliyun.com|g' \
    -e 's|security.debian.org|mirrors.aliyun.com|g' \
    /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y \
        locales \
        gcc \
        libpoppler-cpp-dev \
        poppler-utils \
    && sed -i 's/^# *zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen zh_CN.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Python 包使用阿里云 PyPI
COPY requirements.txt .

RUN pip install --no-cache-dir \
    -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# 复制项目
COPY . .

# 创建运行目录
RUN mkdir -p \
    /app/data \
    /app/pdf \
    /app/excel \
    /app/questions \
    /app/static \
    /app/templates \
    /app/logs

EXPOSE 8765

CMD ["python", "main.py"]