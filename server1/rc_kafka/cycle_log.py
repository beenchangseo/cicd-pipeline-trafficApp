import json, os
import psycopg2
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv(verbose=True, dotenv_path="../../.env")

def put_cycle_log(buf, con):
    lcid = buf[0] - 1
    log_time = "'20%02d-%02d-%02d %02d:%02d:%02d'" % (buf[1], buf[2], buf[3], buf[4], buf[5], buf[6])
    cycle = buf[19]
    offset = buf[21]
    split = buf[43:43 + 16]
    if cycle == 0:
        return
    print("PC-mysql : cycle_log  [id = %d]" % (lcid + 1), log_time, cycle, offset, split[0:8], split[8:16])
    try:
        querry = """INSERT INTO cycle_log(log_time, location_id, cycle, offset_value, split_1, split_2, split_3, split_4, split_5, split_6, split_7, split_8,
                        ped_1, ped_2, ped_3, ped_4, ped_5, ped_6, ped_7, ped_8)
                        VALUES(%s, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d)""" % (
            log_time, lcid + 1, cycle, offset,
            split[0], split[1], split[2], split[3], split[4], split[5], split[6], split[7],
            split[8], split[9], split[10], split[11], split[12], split[13], split[14], split[15])
        con.execute(querry)
        mydb.commit()
    except Exception as e:
        print('Exception in putting cycle_log')
        print(e)


if __name__ == '__main__':
    KAFKA_SERVERS = os.getenv('SERVER1_IP') + ':9092'
    API_VERSION = (0, 10, 1)
    DATABASE_SERVERS = os.getenv('SERVER2_IP')
    mydb = psycopg2.connect(
        host=DATABASE_SERVERS,
        user="postgres",
        password="xhdtlsqhdks1",
        database="tcs_database",
    )
    cursor = mydb.cursor()
    cycle_consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='latest',
        group_id='cycle-logger',
        api_version=API_VERSION)
    cycle_consumer.subscribe(['cycle-log'])
    for msg in cycle_consumer:
        try:
            jsonData = json.loads(msg.value)
            lcbuf = jsonData['cycle']
            print(lcbuf)
            put_cycle_log(lcbuf, cursor)
        except Exception as e:
            print(e)
            continue
