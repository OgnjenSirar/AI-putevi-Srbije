FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/root/.cache/huggingface
WORKDIR /srv
# PyTorch sa CUDA 12.8 bibliotekama (dovoljan je NVIDIA drajver na hostu + NVIDIA Container Toolkit)
RUN pip install torch --index-url https://download.pytorch.org/whl/cu128
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
