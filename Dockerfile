FROM python:3.11.9-slim-bullseye

WORKDIR /var/www/html
ENV PYTHONPATH=/var/www/html/

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git

RUN  git clone https://github.com/yuliiabosher/Fiber-optic-project.git
RUN git branch dashboard-example
RUN git switch dashboard-example
RUN git pull dashboard-example

RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8000

ENTRYPOINT [ "flask" ]
CMD [ "run", "-p", "8000", "--host","0.0.0.0"]
