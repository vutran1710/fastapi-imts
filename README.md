## Setup

Create docker network
```
$ docker network create -d bridge image-tagged-system-network
```

Installing things
```
$ pipenv install --dev --pre
$ cp docker-local.env .env
$ docker-compose up -d
$ pipenv run dev
```
