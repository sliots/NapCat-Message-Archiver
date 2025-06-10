# app.py
import os
import json
import logging
import asyncio
import threading
from datetime import datetime

import websockets
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from flask import Flask
from flask_socketio import SocketIO

# === Config ===
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'PASSWORD'),
    'host': os.getenv('POSTGRES_HOST', '172.17.0.1'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

WS_CONFIG = {
    'url': os.getenv('WS_URL', 'ws://172.17.0.1:3001'),
    'auth_token': os.getenv('WS_AUTH_TOKEN', 'napcat'),
    'reconnect_delay': int(os.getenv('RECONNECT_DELAY', 5))
}

FLASK_CONFIG = {
    'host': os.getenv('FLASK_HOST', '0.0.0.0'),
    'port': int(os.getenv('FLASK_PORT', 5000)),
    'debug': os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
}

# === Logger ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Flask App ===
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# === PostgreSQL Pool ===
db_pool = SimpleConnectionPool(minconn=1, maxconn=5, **DB_CONFIG)

def insert_message(message_data):
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            post_type = message_data.get('post_type')
            message_id = message_data.get('message_id', 0)
            timestamp = datetime.fromtimestamp(message_data.get('time', 0))
            raw = json.dumps(message_data)
            message_content = (message_data.get('message') or '')[:10]

            cur.execute("""
                INSERT INTO qq_messages (post_type, message_id, timestamp, raw)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (post_type, message_id, timestamp) DO NOTHING
            """, (post_type, message_id, timestamp, raw))

            conn.commit()
            logging.info(f"Inserted message: {post_type}, ID: {message_id}, Time: {timestamp}, Content: {message_content}")
    except Exception as e:
        logging.error(f"DB Insert Error: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

# === WebSocket Handler ===
async def listen_to_ws():
    headers = {"Authorization": f"Bearer {WS_CONFIG['auth_token']}"}

    while True:
        try:
            async with websockets.connect(
                WS_CONFIG['url'],
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=60
            ) as ws:
                logging.info(f"Connected to WebSocket at {WS_CONFIG['url']}")
                async for message in ws:
                    try:
                        data = json.loads(message)
                        insert_message(data)
                    except json.JSONDecodeError:
                        logging.warning("Non-JSON message received")
                    except Exception as e:
                        logging.error(f"Processing Error: {e}")
        except Exception as e:
            logging.error(f"WebSocket connection error: {e}. Retrying in {WS_CONFIG['reconnect_delay']}s...")
            await asyncio.sleep(WS_CONFIG['reconnect_delay'])

# === Flask Route ===
@app.route('/')
def index():
    return "NapCatQQ Message Receiver is running"

# === WebSocket Thread ===
def start_ws_thread():
    asyncio.run(listen_to_ws())

# === Main ===
if __name__ == '__main__':
    threading.Thread(target=start_ws_thread, daemon=True).start()
    socketio.run(app, host=FLASK_CONFIG['host'], port=FLASK_CONFIG['port'], debug=FLASK_CONFIG['debug'])
