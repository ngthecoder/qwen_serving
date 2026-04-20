FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update -y && apt install -y python3 python3-pip && ln -s /usr/bin/python3 /usr/bin/python

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY load_model.py ./
RUN python load_model.py

COPY . .

CMD [ "python", "./main.py" ]
