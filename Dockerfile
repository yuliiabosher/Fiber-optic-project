FROM python:3.11.9-slim-bullseye

RUN apt-get update
COPY  /home/$user/Fiber-optic-project/* /var/www/html/

WORKDIR /var/www/html/
ENV PYTHONPATH=/var/www/html/

RUN git pull origin dashboard-example

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 443

ENTRYPOINT [ "flask" ]
CMD [ "run", "-p", "443", "--host","0.0.0.0"]
