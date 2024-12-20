from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import boto3
import pandas as pd
import logging
import requests
import os
import psycopg2

# Конфигурация S3
SELECTEL_ACCESS_KEY = 'your_access_key'
SELECTEL_SECRET_KEY = 'your_secret_key'
SELECTEL_ENDPOINT = 'https://s3.gis-1.storage.selcloud.ru'
S3_BUCKET = 'clients'
S3_KEY = 'credit_clients.csv'
LOCAL_FILE_PATH = '/root/airflow/credit_clients.csv'

# Конфигурация PostgreSQL
PG_HOST = '172.19.0.2'
PG_DATABASE = 'airflow_db'
PG_USER = 'airflow'
PG_PASSWORD = 'airflowpassword'
PG_TABLE = 'credit_clients'

# Конфигурация Superset
SUPSET_URL = 'http://176.114.91.241:8080/superset/'
DASHBOARD_ID = 1

def download_file_from_s3(**kwargs):
    s3 = boto3.client('s3',
        endpoint_url=SELECTEL_ENDPOINT,
        aws_access_key_id=SELECTEL_ACCESS_KEY,
        aws_secret_access_key=SELECTEL_SECRET_KEY,
        region_name='gis-1')
    try:
        s3.download_file(S3_BUCKET, S3_KEY, LOCAL_FILE_PATH)
        logging.info(f"File downloaded successfully from S3: {LOCAL_FILE_PATH}")
    except Exception as e:
        logging.error(f"Failed to download file from S3: {str(e)}")
        raise

def load_data_to_postgres(**kwargs):
    # Загрузка данных из CSV в DataFrame
    df = pd.read_csv(LOCAL_FILE_PATH)

    # Подключение к PostgreSQL
    conn = psycopg2.connect(
        host=PG_HOST,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()

    try:
        # Вставка данных в таблицу
        for index, row in df.iterrows():
            cursor.execute(f"""
                INSERT INTO {PG_TABLE} (Date, CustomerId, Surname, CreditScore, Geography, Gender, Age, Tenure, Balance, NumOfProducts, HasCrCard, IsActiveMember, EstimatedSalary, Exited)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (CustomerId) DO NOTHING;  -- Обработка дубликатов по CustomerId
            """, (row['Date'], row['CustomerId'], row['Surname'], row['CreditScore'], row['Geography'], 
                  row['Gender'], row['Age'], row['Tenure'], row['Balance'], row['NumOfProducts'], 
                  row['HasCrCard'], row['IsActiveMember'], row['EstimatedSalary'], row['Exited']))

        conn.commit()
        logging.info("Data loaded successfully into PostgreSQL.")
    except Exception as e:
        logging.error(f"Error loading data into PostgreSQL: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def refresh_superset_dashboard():
    session = requests.Session()
    
    # Аутентификация
    auth_data = {
        'username': 'admin',  # Укажите ваше имя пользователя Superset
        'password': 'adminpassword',  # Укажите ваш пароль Superset
        'provider': 'db',
        'refresh': True
    }
    response = session.post(f"{SUPSET_URL}/api/v1/security/login", json=auth_data)
    
    if response.status_code != 200:
        logging.error(f"Failed to log in to Superset: {response.text}")  # Изменено на response.text
        return

    # Обновление дашборда
    refresh_response = session.post(f"{SUPSET_URL}/api/v1/dashboard/{DASHBOARD_ID}/refresh")
    
    if refresh_response.status_code == 200:
        logging.info("Dashboard refreshed successfully in Superset.")
    else:
        try:
            error_info = refresh_response.json()  # Попытка декодирования JSON
        except requests.exceptions.JSONDecodeError:
            error_info = refresh_response.text  # Получаем текст ответа, если не удалось декодировать JSON
        logging.error(f"Failed to refresh dashboard: {error_info}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
}

with DAG(dag_id='air-dag',
         default_args=default_args,
         schedule_interval='@hourly',  # Запуск каждый час
         catchup=False) as dag:

    start = DummyOperator(task_id='start')

    download_task = PythonOperator(
        task_id='download_file_from_s3',
        python_callable=download_file_from_s3
    )

    load_data_task = PythonOperator(
        task_id='load_data_to_postgres',
        python_callable=load_data_to_postgres
    )

    refresh_dashboard_task = PythonOperator(
        task_id='refresh_superset_dashboard',
        python_callable=refresh_superset_dashboard
    )

    end = DummyOperator(task_id='end')

    # Определение последовательности задач
    start >> download_task >> load_data_task >> refresh_dashboard_task >> end
