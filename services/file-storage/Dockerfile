FROM python:3.13-slim


RUN mkdir -p /init

COPY init/* /init/

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /init/requirements.txt


CMD ["python", "/init/init.py"]