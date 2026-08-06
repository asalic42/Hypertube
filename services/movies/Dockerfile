FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init
RUN mkdir -p /certs

COPY certs/ca.crt /certs/
COPY init/* /init/

WORKDIR /code

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /init/requirements.txt

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:8443", "movies.wsgi:application"]