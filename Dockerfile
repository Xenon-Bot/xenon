FROM python:3.7

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY xenon/ .

CMD [ "python", "-m", "cProfile", "-o", "profile.txt", "launcher.py" ]
