FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init
RUN mkdir -p /certs
RUN mkdir -p /jwt

COPY certs/ca.crt /certs/
COPY init/* /init/
COPY jwt/jwt_public.pem /jwt/

WORKDIR /code

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /init/requirements.txt

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:8443", "users.wsgi:application"]