FROM python:3.12

WORKDIR /app

# Git LFS インストール 
RUN apt-get update && apt-get install -y git-lfs \
    && git lfs install \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]
