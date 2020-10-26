FROM python:3.8-alpine

WORKDIR /app

ADD requirements.txt .

RUN pip install -r requirements.txt

ADD bot.py .

CMD ["python", "bot.py"]
