# World Models for Model-Based Reinforcement Learning
# Dreamer v3, RSSM, Model-Based RL
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 worldmodel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=worldmodel:worldmodel . .

USER worldmodel

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import torch, gym; print('healthy')" || exit 1

CMD ["python", "train.py"]
