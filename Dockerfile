# `pipecat cloud deploy` builds this image in the cloud. If you build it yourself
# for a custom-image deploy, Daily-hosted regions run Linux on ARM:
#   docker build --platform linux/arm64 -t my-voice-agent:latest .
FROM dailyco/pipecat-base:latest-py3.11

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./bot.py bot.py
