# app.py
import asyncio
import json
import websockets
from flask import Flask
from flask_socketio import SocketIO
import psycopg2
from psycopg2 import sql
from datetime import datetime
import os
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

# Configuration from environment variables with defaults
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'PASSWORD'),
    'host': os.getenv('POSTGRES_HOST', '172.17.0.1'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

WS_CONFIG = {
    'ws_url': os.getenv('WS_URL', 'ws://172.17.0.1:3001'),
    'ws_auth_token': os.getenv('WS_AUTH_TOKEN', 'napcat'),
    'reconnect_delay': int(os.getenv('RECONNECT_DELAY', '5'))
}

FLASK_CONFIG = {
    'host': os.getenv('FLASK_HOST', '0.0.0.0'),
    'port': int(os.getenv('FLASK_PORT', '5000')),
    'debug': os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
}

# Insert message to database
def insert_message_to_db(message_data):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        post_type = message_data.get('post_type')
        message_id = message_data.get('message_id', 0)
        timestamp = datetime.fromtimestamp(message_data.get('time', 0))
        raw = json.dumps(message_data)
        
        insert_query = sql.SQL("""
        INSERT INTO qq_messages (
            post_type, message_id, timestamp, raw
        ) VALUES (%s, %s, %s, %s)
        ON CONFLICT (post_type, message_id, timestamp) 
        DO NOTHING
        """)
        
        cursor.execute(insert_query, (
            post_type,
            message_id,
            timestamp,
            raw
        ))
        conn.commit()
        print("Message stored in database")
    except Exception as e:
        print(f"Error storing message: {e}")
    finally:
        if conn:
            conn.close()

# WebSocket handler
async def napcat_websocket_handler():
    headers = {"Authorization": f"Bearer {WS_CONFIG['ws_auth_token']}"}
    
    while True:
        try:
            async with websockets.connect(
                WS_CONFIG['ws_url'],
                additional_headers=headers,
                ping_interval=30,
                ping_timeout=60
            ) as websocket:
                print(f"Connected to NapCatQQ WebSocket at {WS_CONFIG['ws_url']}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        print(f"Received message: {message}")
                        
                        try:
                            message_data = json.loads(message)
                            insert_message_to_db(message_data)
                            
                        except json.JSONDecodeError:
                            print("Received non-JSON message")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed, reconnecting...")
                        break
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        break
                        
        except Exception as e:
            print(f"WebSocket connection error: {e}, retrying in {WS_CONFIG['reconnect_delay']}s...")
            await asyncio.sleep(WS_CONFIG['reconnect_delay'])

# Flask route
@app.route('/')
def index():
    return "NapCatQQ Message Receiver Service is running"

# Start WebSocket client
def start_websocket_client():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(napcat_websocket_handler())

if __name__ == '__main__':    
    # Start WebSocket client in a thread
    ws_thread = threading.Thread(target=start_websocket_client)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Start Flask app
    socketio.run(app, 
                host=FLASK_CONFIG['host'], 
                port=FLASK_CONFIG['port'], 
                debug=FLASK_CONFIG['debug'])
