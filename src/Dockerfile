FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
WORKDIR /app

RUN apt update -y && apt upgrade -y
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt update
RUN apt install python3.12 python3-pip -y
RUN ln -s /usr/bin/python3.12 /usr/bin/python

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY load_model.py ./
RUN python load_model.py

COPY . .

CMD [ "python", "./main.py" ]
