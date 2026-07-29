FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init
RUN mkdir -p /certs

COPY certs/* /certs
COPY init/* /init/
# COPY volumes/app-users/ /code/

RUN mkdir -p /usr/local/share/ca-certificates
RUN cp /certs/ca.crt /usr/local/share/ca-certificates/ca.crt

WORKDIR /code

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r /init/requirements.txt

EXPOSE 8000

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]