FROM python:3.13.5

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init

WORKDIR /code

RUN pip install --upgrade pip

COPY services/users/app_users/init/ /init/
COPY volumes/users/app_users/ /code/

RUN pip install --no-cache-dir -r /init/requirements.txt

EXPOSE 8000

ENTRYPOINT ["bash", "/init/init.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]