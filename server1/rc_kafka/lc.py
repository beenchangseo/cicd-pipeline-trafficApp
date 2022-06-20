"""

2022 / 01 / 19
write by SCB

"""
import json, os, sys, threading, time
from socket import *
from kafka import KafkaProducer, KafkaConsumer
import psycopg2
from dotenv import load_dotenv

load_dotenv(verbose=True, dotenv_path="../../.env")

print('""""""""""""""""""""""""""""""\n\t2022 / 01 / 19\n\tWrite By SCB\n""""""""""""""""""""""""""""""')

lc_msg = [0] * 64
request_command_queue = []

Sync_TIME = 600
DATABASE_SERVER = os.getenv('SERVER2_IP')             # DATABASE 서버
KAFKA_SERVERS = os.getenv('SERVER1_IP') + ':9092'     # KAFKA 서버
API_VERSION = (0, 10, 1)  # KAFKA 버전
PORT_NUM = 7070
sockConnect = False  # SERVER - L/C 연결 상태
stop_threads = False

print("[CONFIG] KAFKA SERVER : ", KAFKA_SERVERS)
print("[RUN] KAFKA Producer, Consumer 생성")
kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_SERVERS, api_version=API_VERSION)
cmd_consumer = KafkaConsumer(
    bootstrap_servers=KAFKA_SERVERS,
    auto_offset_reset='latest',
    group_id='COMMAND_CSM' + sys.argv[1],
    # consumer_timeout_ms=10000,
    api_version=API_VERSION)
cmd_consumer.subscribe(['LC-COMMAND'])
print("[RUN COMPLETE] KAFKA Producer, Consumer 생성")

# kafka producer function
def publish_message(producer, topic_name, key, value):
    try:
        data = {key: value}
        producer.send(topic_name, json.dumps(data).encode())
    except Exception as e:
        print('Exception in publishing message ->', e)

# pretty printer bytearray
def hex_dump(msg, buf):
    for value in buf: msg += " %02X" % value
    print(msg)

# LRC Generator
def gen_lrc(buf):
    lrc = 0
    for value in buf: lrc ^= value
    return lrc

# (교차로 상황 정보 업로드 명령어 + 시계 업로드 명령어)
def send(lcid):
    sts_sndmsg = [0x7e, 0x7e, 4, lcid % 16, 0x12]
    sts_sndmsg.append(gen_lrc(sts_sndmsg))
    clock_sndmsg = [0x7e, 0x7e, 4, lcid % 16, 0x42]
    clock_sndmsg.append(gen_lrc(clock_sndmsg))
    return bytearray(clock_sndmsg + sts_sndmsg)

# buffer(소켓) OPCODE 확인하여 알맞은 KAFKA TOPIC으로 Produce
def make_kafka_msg(buffer):
    if buffer[4] == 0x13:                           # LC status
        if buffer[2] < 29 or buffer[2] == 32:       # 4색 제어기
            lc_msg[8:8 + 17] = buffer[5:5 + 17]     # LC status
            lc_msg[24] |= 0x80                      # 4색 제어기 표시
            lc_msg[26] = buffer[11] & 0x01          # detector ch 1
            lc_msg[26] += (buffer[11] & 0x02) << 1  # detector ch 2
            lc_msg[26] += (buffer[11] & 0x04) << 2  # detector ch 3
            lc_msg[26] += (buffer[11] & 0x08) << 3  # detector ch 4
        else:                                       # 3색 제어기
            lc_msg[8:8 + 25] = buffer[5:5 + 25]

                                                    # calculate remain time
        phase = (lc_msg[9] >> 5) + 1
        cycle = lc_msg[20]
        split = 0
        for i in range(phase): split += lc_msg[35 + i]
        if cycle > 0:
            lc_msg[59] = (cycle + split - lc_msg[18]) % cycle

    elif buffer[4] == 0x23:                             # detector information
        lc_msg[27:27 + 8] = buffer[5 + 96:5 + 96 + 8]   # vol 1-8
        lc_msg[35:35 + 8] = buffer[5 + 64:5 + 64 + 8]   # occ 1-8
        lc_msg[60] = (lc_msg[60] + 1) & 0x7f            # split upload
        """
            2022 / 01 / 12
            0x23 -> detect-log 토픽으로 검지기 채널 vol & occ 정보 생성
        """
        print("[KAFKA (detect-log)]", lc_msg)
        publish_message(kafka_producer, 'detect-log', 'detect', lc_msg)
    elif buffer[4] == 0x33:                                     # split
        lc_msg[43: 43 + 8] = buffer[5: 5 + 8]                   # vehicle split

        if buffer[2] > 20:                                      # if 3색 제어
            lc_msg[51: 51 + 8] = buffer[5 + 16: 5 + 16 + 8]     # ped time
        """
            2022 / 01 / 12
            0x33 -> cycle-log 토픽으로 vehicle split & ped time 정보 생성
        """
        print("[KAFKA (cycle-log)]", lc_msg)
        publish_message(kafka_producer, 'cycle-log', 'cycle', lc_msg)

    elif buffer[4] == 0x43:                                     # clock upload
        BASE = 4
        lc_msg[1] = buffer[BASE + 1]                            # year
        lc_msg[2] = buffer[BASE + 2]                            # month
        lc_msg[3] = buffer[BASE + 3]                            # day
        lc_msg[4] = buffer[BASE + 4]                            # hour
        lc_msg[5] = buffer[BASE + 5]                            # min
        lc_msg[6] = buffer[BASE + 6]                            # sec
        lc_msg[7] = (lc_msg[7] & 0xf0) + (buffer[BASE + 7] & 0x0f)

    else:
        print(buffer)


def sync_clock(sock, lcid):
    timer = 0
    print("[RUN] sync_clock thread start")
    while True:
        if stop_threads:
            break
        if timer == Sync_TIME:
            t = time.localtime()  # 현재 센터 서버 시간
            command = [0x7e, 0x7e, 0x0b, lcid % 16, 0x40]
            command[5:] = [t.tm_year % 100, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, (t.tm_wday + 1) & 0x7]
            command.append(gen_lrc(command))
            sock.send(bytearray(command))
            timer = 0
        time.sleep(1)
        timer += 1
    print("[LOG] sync_clock thread stop")


def command_sender(lcid, consumer):
    print("[RUN] command_sender thread start")
    for msg in consumer:  # 업다운 명령어 토픽 구독
        jsonData = json.loads(msg.value)
        try:
            buf = jsonData['command']  # 토픽 Datad의 'command' 읽어오기
            if buf[3] == lcid:  # Socket 연결 시 sys.argv[1]의 LCID 명령어만 전송
                request_command_queue.append(bytearray(buf))
            else:
                pass
        except Exception as e:
            print('[LOG] thread -> command_sender exception...', e)
            pass
    print("[LOG] command_sender thread stop")


def rx_handler(rxmsg, lcid):
    if rxmsg[4] >= 0x50:  # 제어기 DATABASE 업다운로드 결과 > 0x50
        if rxmsg[3] != lcid:
            rxmsg[3] = lcid  # 업로드 LCID 값이 다르게 올라오면 제어기 번호 강제 수정
        # hex_dump("[RX(control-rsp)] ", rxmsg)

        # control-response topic publish...
        print("[KAFKA (command-response)]", rxmsg)
        publish_message(kafka_producer, 'command-response', 'command', rxmsg)
    else:
        # hex_dump("[RX(non-control)] ", rxmsg)
        make_kafka_msg(rxmsg)


if __name__ == "__main__":
    lcId = None
    if len(sys.argv) < 2:  # argv 인자 값 유무 확인
        print("교차로 ID 인자 값을 입력 해 주세요.")
        sys.exit()
    else:
        print("[RUN] Python File: {}, argv:  {}".format(sys.argv[0], sys.argv[1]))  # 인자 값 로그 출력
        lcId = int(sys.argv[1]) % 100
    lc_msg[0] = lcId

    conn = psycopg2.connect(
        host=DATABASE_SERVER,
        user="postgres",
        password="xhdtlsqhdks1",
        database="tcs_database",
    )
    cursor = conn.cursor()
    cursor.execute('select "location_lcIp" from location order by "location_id"')
    server_address = (cursor.fetchall()[lcId - 1][0], PORT_NUM)
    conn.close()
    t2 = threading.Thread(target=command_sender, args=(lcId, cmd_consumer,))
    t2.daemon = True
    t2.start()
    while True:
        try:
            if not sockConnect:
                print("[RUN] {} CONNECTION 생성".format(server_address))
                clientSock = socket(AF_INET, SOCK_STREAM)
                clientSock.settimeout(4)
                clientSock.connect(server_address)
                print("[RUN COMPLETE] {} CONNECTION 생성".format(server_address))
                sockConnect = True
                stop_threads = False
                t1 = threading.Thread(target=sync_clock, args=(clientSock, lcId,))
                t1.daemon = True
                t1.start()


            if len(request_command_queue) > 0:
                clientSock.send(request_command_queue.pop(0))
                time.sleep(1)
            else:
                clientSock.send(send(lcId))
                time.sleep(2)

            rcvmsg = []
            rcvmsg += clientSock.recv(1024)

            if len(rcvmsg) >= (rcvmsg[2] + 2):
                while len(rcvmsg) != 0:
                    rx_length = rcvmsg[2] + 2
                    rx = rcvmsg[0:rx_length]
                    del rcvmsg[0:rx_length]
                    rx_handler(rx, lcId)
            else:
                rx_handler(rcvmsg, lcId)

            publish_message(kafka_producer, 'local-kafka', 'STS', lc_msg)
            print("[KAFKA (local-kafka)]", lc_msg)

        except Exception as e:
            print("[ERR] Socket connection Error[lcid = %d]->" % lcId, e)
            clientSock.close()
            sockConnect = False
            stop_threads = True
            t1.join()
            time.sleep(5)
            continue
