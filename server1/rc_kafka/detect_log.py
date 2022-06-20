import json, os
import psycopg2
from kafka import KafkaConsumer
from dotenv import load_dotenv

load_dotenv(verbose=True, dotenv_path="../../.env")

def put_detect_log(buf, con):
    lcid = buf[0] - 1
    log_time = "'20%02d-%02d-%02d %02d:%02d:%02d'" % (buf[1], buf[2], buf[3], buf[4], buf[5], buf[6])
    cycle = buf[19]
    vol = buf[27:27 + 8]
    occ = buf[35:35 + 8]
    if cycle == 0:
        return
    print("PC-mysql : detect_log [id = %d]" % (lcid + 1), log_time, vol, occ)
    try:
        querry = """INSERT INTO detect_log(log_time, location_id, vol_1, occ_1, vol_2, occ_2, vol_3, occ_3, vol_4, occ_4,
                            vol_5, occ_5, vol_6, occ_6, vol_7, occ_7, vol_8, occ_8)
                            VALUES(%s, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d)""" % (
            log_time, lcid + 1,
            vol[0], occ[0], vol[1], occ[1], vol[2], occ[2], vol[3], occ[3],
            vol[4], occ[4], vol[5], occ[5], vol[6], occ[6], vol[7], occ[7])
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
    detect_consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='latest',
        group_id='detect-logger',
        api_version=API_VERSION)
    detect_consumer.subscribe(['detect-log'])
    for msg in detect_consumer:
        try:
            jsonData = json.loads(msg.value)
            lcbuf = jsonData['detect']
            put_detect_log(lcbuf, cursor)
        except Exception as e:
            print(e)
            continue
