import json, os
import psycopg2
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv

load_dotenv(verbose=True, dotenv_path="../../.env")

KAFKA_SERVERS = os.getenv('SERVER1_IP') + ':9092'
API_VERSION = (0, 10, 1)
DATABASE_SERVERS = os.getenv('SERVER2_IP')
kafka_producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVERS,
    api_version=API_VERSION
)
lc_status = [0] * 50

def publish_message(producer, topic_name, key, value):
    try:
        data = {key: value}
        producer.send(topic_name, json.dumps(data).encode())
    except Exception as e:
        print('Exception in publishing message')
        print(e)

def check_lc_event(buf, con):
    global lc_status
    lcid = buf[0] - 1
    current = (buf[7] >> 4) + (buf[8] & 0xe0)  # code 0  - 7
    current += (buf[11]) << 8  # code 8  - 15
    current += (buf[12] & 0x8f) << 16  # code 16 - 23
    xor = lc_status[lcid] ^ current
    lc_status[lcid] = current
    log_time = "'20%02d-%02d-%02d %02d:%02d:%02d'" % (buf[1], buf[2], buf[3], buf[4], buf[5], buf[6])
    for i in range(32):
        if xor & 0x000001:
            event_code = i
            event_state = current & 0x000001
            print("PC-mysql : event-log  [id = %d]" % (lcid + 1), log_time, event_code, event_state)
            put_event_log(con, log_time, lcid + 1, event_code, event_state)
            publish_message(kafka_producer, 'event-log', 'LOG', [log_time, lcid + 1, event_code, event_state])
        current = current >> 1
        xor = xor >> 1
    return

def put_event_log(con, log_time, lc_id, event_code, event_status):
    try:
        querry = """INSERT INTO event_log(log_time, location_id, event_code, event_status)
            VALUES(%s, %d, %d, %d)""" % (log_time, lc_id, event_code, event_status)
        con.execute(querry)
        mydb.commit()
    except Exception as e:
        print('Exception in putting event_log')
        print(e)

if __name__ == '__main__':
    mydb = psycopg2.connect(
        host=DATABASE_SERVERS,
        user="postgres",
        password="xhdtlsqhdks1",
        database="tcs_database",
    )
    cursor = mydb.cursor()
    event_consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='latest',
        group_id='event-logger',
        api_version=API_VERSION)
    event_consumer.subscribe(['local-kafka'])
    for msg in event_consumer:
        try:
            jsonData = json.loads(msg.value)
            lcbuf = jsonData['STS']
            check_lc_event(lcbuf, cursor)
        except Exception as e:
            print(e)
            continue
