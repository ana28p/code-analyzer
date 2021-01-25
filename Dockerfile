FROM python:3.8

ENV DASH_DEBUG_MODE False

RUN mkdir -p /app
COPY ./tool /app
WORKDIR /app
RUN set -ex && \
    pip install -r requirements.txt
EXPOSE 8050

CMD ["python", "app.py"]