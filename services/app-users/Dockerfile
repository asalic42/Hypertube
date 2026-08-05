FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init

RUN mkdir -p /certs
COPY certs/ca.crt /certs/
COPY init/* /init/

RUN mkdir -p /usr/local/share/ca-certificates

WORKDIR /code

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r /init/requirements.txt

EXPOSE 8000

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]