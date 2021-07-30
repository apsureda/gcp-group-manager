FROM python:3-alpine

COPY scripts/*.* ./
RUN pip install --no-cache-dir -r requirements.txt

COPY templates ./templates

COPY . .

ENTRYPOINT ["python"]
