FROM python:3.13.5

ENV PYTHONBUFFERED=1

RUN mkdir -p /code
RUN mkdir -p /init

COPY init/* /init

WORKDIR /code


ENTRYPOINT ["bash", "/conf/init.sh"]
CMD [""]