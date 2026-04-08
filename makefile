# ОДНА КОМАНДА, ЧТОБЫ УПРАВЛЯТЬ ВСЕМ

all: venv-create venv-activate requirements-install docker-all-run

# временно так
dev: fastapi dev


ifeq ($(OS),Windows_NT)
    PYTHON := python
    PIP := pip
    VENV_ACTIVATE := venv\Scripts\activate.bat
    VENV_CREATE := python -m venv venv
else
    PYTHON := python3
    PIP := pip3
    VENV_ACTIVATE := source venv/bin/activate
endif


# УСТАНОВКА

requirements-add:
	$(PIP) freeze > requirements.txt

requirements-install:
	$(PIP) install -r requirements.txt

venv-create:
	$(PYTHON) -m venv venv

venv-delete:
	rm -rf venv/

venv-activate:
	$(VENV_ACTIVATE)


# ЗАПУСК

docker-all-run:
	docker-compose up

docker-all-restart:
	docker-compose restart

docker-all-stop:
	docker-compose stop

docker-app-build:
	docker build -t app:latest .

docker-app-restart:
	docker-compose restart app

docker-arangodb-restart:
	docker-compose restart arangodb

app-local:
	fastapi dev


# УТИЛИТЫ

test:
	pytest main.py


# ЯРЛЫКИ

mm:
	git pull origin development
m: app-local
v: venv-activate
vv: venv-create
d: docker-all-run
dd: docker-app-restart
db: docker-arangodb-restart
r: requirements-install
rr: docker-app-build
t: test
tt:
	$(PYTHON) test_data.py
