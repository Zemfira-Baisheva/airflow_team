# README

## Описание проекта

Этот проект представляет собой платформу, работающую с базой данных, развернутой в контейнерах Docker. В этом файле содержится инструкция по настройке и использованию платформы с нуля.

## Требования

Перед началом работы убедитесь, что у вас установлены следующие компоненты:


- Miniconda (https://docs.anaconda.com/miniconda/install/)
- [Docker](https://www.docker.com/get-started)

## Установка и настройка
1. Создание пользовательской сети Docker
Для того чтобы контейнеры могли обмениваться данными между собой, нужно создать пользовательскую сеть в Docker. 
Таким образом, оба контейнера смогут общаться по имени хоста.

3. Запуск контейнера PostgreSQL

Запустим контейнер с PostgreSQL, используя эту сеть. Мы также укажем параметры для базы данных, такие как имя пользователя и пароль.
docker run --rm -d \
    --network superset_network \
    --name postgres \
    -e POSTGRES_USER=airflow \
    -e POSTGRES_PASSWORD=airflowpassword \
    -e POSTGRES_DB=airflow_db \
    -p 5432:5432 \
    postgres:latest
    
3. Запуск контейнера с Apache Superset

Теперь запустим контейнер с Apache Superset, который будет подключаться к PostgreSQL через ту же сеть Docker.

docker run --rm -d \
    --network superset_network \
    --name superset \
    -p 8080:8088 \
    -e "SUPERSET_SECRET_KEY=$(openssl rand -base64 42)" \
    apache/superset
    
4. Инициализация базы данных Superset

Перед тем как начать использовать Superset, необходимо инициализировать базу данных. Для этого выполните команду в Docker:

docker exec -it superset superset db upgrade

5. Создание администратора Superset

Для создания пользователя-администратора выполните следующую команду:

docker exec -it superset superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@superset.com \
    --password adminpassword
    
6. Запуск веб-сервера Superset

Теперь запустите веб-сервер Superset:
docker exec -it superset superset run -p 8080 --with-threads --reload --debugger

Шаги для загрузки данных из CSV в PostgreSQL:
1. Скачайте CSV-файл. Для этого вы можете использовать wget или curl. Пример с использованием wget:
wget https://9c579ca6-fee2-41d7-9396-601da1103a3b.selstorage.ru/credit_clients.csv

2. Создайте базу данных в PostgreSQL (если она еще не создана). Войдите в контейнер PostgreSQL:
docker exec -it postgres psql -U airflow -d airflow_db -W


CREATE TABLE credit_clients (
    Date DATE,
    CustomerId BIGINT PRIMARY KEY,
    Surname VARCHAR(255),
    CreditScore INT,
    Geography VARCHAR(100),
    Gender VARCHAR(10),
    Age INT,
    Tenure INT,
    Balance DECIMAL(10, 2),
    NumOfProducts INT,
    HasCrCard INT,
    IsActiveMember INT,
    EstimatedSalary DECIMAL(15, 2),
    Exited INT
);


3. Импорт данных из CSV:
Теперь, когда таблица создана, вам нужно загрузить данные из CSV-файла в PostgreSQL.

Сначала убедитесь, что файл credit_clients.csv находится в контейнере PostgreSQL. Вы можете сделать это с помощью команды:

docker cp /path/to/credit_clients.csv postgres:/tmp/credit_clients.csv

Затем, подключитесь к контейнеру PostgreSQL:

docker exec -it postgres psql -U airflow -d airflow_db -W

Используйте команду COPY для импорта данных из файла в таблицу:

COPY credit_clients (Date, CustomerId, Surname, CreditScore, Geography, Gender, Age, Tenure, Balance, NumOfProducts, HasCrCard, IsActiveMember, EstimatedSalary, Exited)
FROM '/tmp/credit_clients.csv'
DELIMITER ','
CSV HEADER;

4. Проверьте импортированные данные:

Чтобы убедиться, что данные были успешно импортированы, выполните запрос:

SELECT * FROM credit_clients LIMIT 10;

Настройка публичного доступа
1. Включите "public" роль в Superset
2. Настройте публичный доступ к дашбордам
3. Настройте конфигурацию Superset для публичного доступа
В конфигурации superset_config.py нужно установить следующие параметры:
 GNU nano 7.2                                        superset_config.py                                                  
# superset_config.py

AUTH_TYPE = 1  # Публичный доступ
PUBLIC_ROLE_LIKE = 'Gamma'  # Роль с ограниченными правами

# Настройки веб-сервера
SUPERSET_WEBSERVER_ADDRESS = "0.0.0.0"  # Доступно на всех интерфейсах
SUPERSET_WEBSERVER_PORT = 8088  # Порт, на котором работает Superset

Если конфигурационного файла нет, создайте его (но перед этим перейдите в папку app):
nano superset_config.py

4. Примените изменения и перезапустите Superset
docker restart superset

ваш дашборд будет доступен по ссылке 
http://your-superset-server:8088/superset/dashboard/your-dashboard-id/

## Настройка автоматической подгрузки данных в БД

### Создание DAG в Airflow

1. Создайте виртуальное окружение

    conda create -n af python==3.12

2. Установите Apache Airflow:

- export AIRFLOW_HOME=~/airflow

- AIRFLOW_VERSION=2.10.4

    # Extract the version of Python you have installed. If you're currently using a Python version that is not supported by Airflow, you may want to set this manually.
    # See above for supported versions.
    PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
    # For example this would install 2.10.4 with python 3.8: https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.8.txt

    pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

- airflow db migrate

3. Создаейте пользователя
    airflow users create \
    --username admin \
    --firstname укажи_имя \
    --lastname укажи_фамилию \
    --role Admin \
    --email user@mail.com

4. В виртуальном окружении с Airflow устанавите драйвер для подключения к Postgres:
- pip install apache-airflow-providers-postgres


5. Создайте DAG, который будет выполняться каждый час:

   ```python
   from airflow import DAG
   from airflow.operators.python_operator import PythonOperator
   from datetime import datetime, timedelta
   import pandas as pd
   from sqlalchemy import create_engine

   def load_data():
       # Скачивание данных из S3
       # Загрузка данных в PostgreSQL
       pass

   default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
   }

6. Запустите веб-сервер:

-airflow webserver --port 8081

7. Запустите планировщик (в отдельной консоли активируем созданное окружение):

- airflow scheduler

