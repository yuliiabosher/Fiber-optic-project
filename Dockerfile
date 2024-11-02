FROM python:3.11.9-slim-bullseye

WORKDIR /app
ENV PYTHONPATH=src

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8000

ENTRYPOINT [ "flask" ]
CMD [ "run", "-p", "8000", "--host","0.0.0.0"]
