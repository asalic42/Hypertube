FROM docker.io/library/python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init

WORKDIR /code

RUN pip install --upgrade pip

COPY services/auth/init/ /init/
COPY volumes/auth/ /code/

RUN pip install --no-cache-dir -r /init/requirements.txt

EXPOSE 8001

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]