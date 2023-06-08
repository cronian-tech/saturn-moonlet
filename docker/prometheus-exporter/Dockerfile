FROM python:3.11.3-alpine

COPY requirements.txt ./
RUN set -eux; \
    pip install --upgrade pip; \
    pip install --no-deps -r requirements.txt

COPY main.py ./

CMD ["python", "main.py"]
