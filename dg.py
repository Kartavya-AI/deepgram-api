import asyncio
import websockets
import json
import ssl
import certifi

async def test_deepgram():
    api_key = "68ea08e124b23d0ce4712297b91237e9b89799bb"
    
    # Create SSL context with proper certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        async with websockets.connect(
            "wss://agent.deepgram.com/v1/agent/converse",
            subprotocols=["token", api_key],
            ssl=ssl_context
        ) as ws:
            print("Connected to Deepgram!")
            config = {"type": "Settings", "audio": {"input": {"encoding": "mulaw", "sample_rate": 8000}}}
            await ws.send(json.dumps(config))
            print("Config sent!")
    except Exception as e:
        print(f"Deepgram connection failed: {e}")

asyncio.run(test_deepgram())