FROM python:3.11.9-slim-bullseye

ENV UDEV=on

RUN apt-get update

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git && \
    apt-get install --yes --no-install-recommends bash


WORKDIR /var/www/html/
ENV PYTHONPATH=/var/www/html/

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["python" , "app.py"]
