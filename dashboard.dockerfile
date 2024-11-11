FROM python:3.11.9-slim-bullseye

ENV UDEV=on

RUN apt-get update

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git && \
    apt-get install --yes --no-install-recommends bash

RUN  git clone https://github.com/yuliiabosher/Fiber-optic-project.git -b dashboard-example /var/www/html

WORKDIR /var/www/html/
ENV PYTHONPATH=/var/www/html/

RUN git pull origin dashboard-example

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["bash" , "/var/www/html/bin/balena_run.sh"]
