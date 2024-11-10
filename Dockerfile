FROM python:3.11.9-slim-bullseye

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git

RUN  git clone https://github.com/yuliiabosher/Fiber-optic-project.git -b dashboard-example /var/www/html

WORKDIR /var/www/html/
ENV PYTHONPATH=/var/www/html/

RUN git pull origin dashboard-example

RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 443

ENTRYPOINT [ "flask" ]
CMD [ "run", "-p", "443", "--host","0.0.0.0"]
