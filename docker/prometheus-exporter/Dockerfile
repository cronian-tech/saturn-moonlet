FROM python:3.12.0-alpine

COPY requirements.txt ./
RUN set -eux; \
    pip install --upgrade pip; \
    pip install --no-deps -r requirements.txt

COPY main.py ./

CMD ["python", "main.py"]
