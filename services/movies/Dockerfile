FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init
RUN mkdir -p /certs
RUN mkdir -p /jwt
RUN mkdir -p /downloads

# ffmpeg converts the videos browsers cannot play (mkv, avi, ...)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY certs/ca.crt /certs/
COPY init/* /init/
COPY jwt/jwt_public.pem /jwt/

WORKDIR /code

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /init/requirements.txt

ENTRYPOINT ["bash", "/init/init.sh"]
# Threaded workers: a video stream holds its connection for a long time
CMD ["gunicorn", "--reload", "--worker-class", "gthread", "--workers", "2", "--threads", "16", "--bind", "0.0.0.0:8443", "movies.wsgi:application"]