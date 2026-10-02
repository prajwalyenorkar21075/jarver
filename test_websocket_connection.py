import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/api/coding/ws/test_session_123"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            # Send a test message
            await websocket.send(json.dumps({"message": "Hello Jarvis", "active_file": "test.py"}))
            
            # Receive response
            status = await websocket.recv()
            print(f"Received status: {status}")
            
            result = await websocket.recv()
            print(f"Received result: {result}")
            
    except Exception as e:
        print(f"WebSocket test failed: {e}")

asyncio.run(test_websocket())
