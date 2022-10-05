FROM python:3.10-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBEFFERED=1

WORKDIR /src

COPY . /src

RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt
ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && apt install -y --no-install-recommends locales; rm -rf /var/lib/apt/lists/*; sed -i '/^#.* uk_UA.UTF-8 /s/^#//' /etc/locale.gen; locale-gen

RUN locale -a