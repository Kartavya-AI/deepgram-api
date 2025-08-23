import asyncio
import base64
import json
import sys
import websockets
import ssl
import os
import certifi

def sts_connect():
    # you can run export DEEPGRAM_API_KEY="your key" in your terminal to set your API key.
    api_key = "cc262d20b3ee02bbd090fe98f678b2bd36a1e894"
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    sts_ws = websockets.connect(
        "wss://agent.deepgram.com/v1/agent/converse",
        subprotocols=["token", api_key],
        ssl=ssl_context
    )
    return sts_ws


async def twilio_handler(twilio_ws):
    print("=== TWILIO HANDLER STARTED ===")
    try:
        audio_queue = asyncio.Queue()
        streamsid_queue = asyncio.Queue()

        print("Connecting to Deepgram...")
        async with sts_connect() as sts_ws:
            print("Connected to Deepgram successfully")
            config_message = {
                "type": "Settings",
                "audio": {
                    "input": {
                        "encoding": "mulaw",
                        "sample_rate": 8000,
                    },
                    "output": {
                        "encoding": "mulaw",
                        "sample_rate": 8000,
                        "container": "none",
                    },
                },
                "agent": {
                    "language": "en",
                    "listen": {
                        "provider": {
                            "type": "deepgram",
                            "model": "nova-3",
                            "keyterms": ["hello", "goodbye"]
                        }
                    },
                    "think": {
                        "provider": {
                            "type": "open_ai",
                            "model": "gpt-4o-mini",
                            "temperature": 0.7
                        },
                        "prompt": """
		Core Identity & Mission
You are a professional AI voice agent representing Kartavya, a cutting-edge AI solutions company. Your primary goal is to engage potential business clients through cold calls, understand their business challenges, and convert them into customers for custom AI solution development.
Company Background - Kartavya

Industry: AI Solutions Development & Implementation
Specialization: Custom AI applications, automation, machine learning solutions
Target Market: Businesses looking to optimize operations, reduce costs, and increase efficiency through AI
Unique Value: Tailored AI solutions that solve specific business problems

Call Structure & Flow
1. Opening (15-20 seconds)

Greeting: Warm, professional tone
Introduction: State your name, company, and purpose briefly
Permission: Ask for a moment of their time
Hook: Lead with a compelling benefit or pain point

Example Opening:
"Hi [Name], this is [Agent Name] from Kartavya AI Solutions. I hope I'm catching you at a good time? I'm calling because we've been helping businesses like yours reduce operational costs by up to 40% through custom AI implementations. Do you have just 2 minutes to explore how this might benefit [Company Name]?"
2. Discovery Phase (60-90 seconds)
Ask strategic questions to identify pain points:

"What's your biggest operational challenge right now?"
"Are you currently using any automation or AI tools?"
"How much time does your team spend on repetitive tasks daily?"
"What would saving 10-15 hours of manual work per week mean for your business?"

3. Value Proposition (45-60 seconds)
Based on their responses, present relevant solutions:

Process Automation: "We can automate your [specific process] using AI"
Data Analytics: "Our AI can analyze your data to provide actionable insights"
Customer Service: "AI chatbots that handle 80% of customer inquiries"
Predictive Analytics: "Forecast demand, inventory, or market trends"

4. Social Proof (30 seconds)
Share relevant success stories:
"We recently helped a [similar industry] company automate their [relevant process], resulting in [specific benefit - cost savings, time reduction, revenue increase]."
5. Closing & Next Steps (30-45 seconds)

Gauge interest level
Offer specific next step (demo, consultation, case study)
Create urgency without being pushy
Schedule follow-up				
	  """
                    },
                    "speak": {
    "provider": {
      "type": "cartesia",
      "model_id": "sonic-2",
      "voice": {
        "mode": "id",
        "id": "9358571b-7f13-41a0-b222-112c748eb31c"
	    },
      "language": "en"
    },
    "endpoint": {
      "url": "https://api.cartesia.ai/tts/bytes",
      "headers": {
        "x-api-key": "sk_car_jW6nNtuyFW3yY1wMHF6gLs"
        }
      }
    },

                    "greeting": "Hello! How can I help you today?"
                }
            }

            await sts_ws.send(json.dumps(config_message))

            async def sts_sender(sts_ws):
                print("sts_sender started")
                try:
                    while True:
                        chunk = await audio_queue.get()
                        if chunk is None:  # Sentinel value to stop
                            break
                        await sts_ws.send(chunk)
                        print(f"Sent {len(chunk)} bytes to Deepgram")
                except Exception as e:
                    print(f"Error in sts_sender: {e}")
                finally:
                    print("sts_sender ended")

            async def sts_receiver(sts_ws):
                print("sts_receiver started")
                try:
                    # we will wait until the twilio ws connection figures out the streamsid
                    streamsid = await streamsid_queue.get()
                    print(f"Got stream ID: {streamsid}")
                    
                    # for each sts result received, forward it on to the call
                    async for message in sts_ws:
                        if type(message) is str:
                            print(f"Deepgram message: {message}")
                            # handle barge-in
                            try:
                                decoded = json.loads(message)
                                if decoded['type'] == 'UserStartedSpeaking':
                                    print("User started speaking - clearing audio")
                                    clear_message = {
                                        "event": "clear",
                                        "streamSid": streamsid
                                    }
                                    await twilio_ws.send(json.dumps(clear_message))
                            except json.JSONDecodeError as e:
                                print(f"Failed to decode JSON: {e}")
                            continue

                        print(f"Received audio chunk: {len(message)} bytes")
                        raw_mulaw = message

                        # construct a Twilio media message with the raw mulaw
                        media_message = {
                            "event": "media",
                            "streamSid": streamsid,
                            "media": {"payload": base64.b64encode(raw_mulaw).decode("ascii")},
                        }

                        # send the TTS audio to the attached phonecall
                        await twilio_ws.send(json.dumps(media_message))
                        
                except Exception as e:
                    print(f"Error in sts_receiver: {e}")
                finally:
                    print("sts_receiver ended")

            async def twilio_receiver(twilio_ws):
                print("twilio_receiver started")
                try:
                    # twilio sends audio data as 160 byte messages containing 20ms of audio each
                    # we will buffer 20 twilio messages corresponding to 0.4 seconds of audio to improve throughput performance
                    BUFFER_SIZE = 20 * 160

                    inbuffer = bytearray(b"")
                    async for message in twilio_ws:
                        try:
                            data = json.loads(message)
                            print(f"Twilio event: {data.get('event', 'unknown')}")
                            
                            if data["event"] == "start":
                                print("Call started - got our streamsid")
                                start = data["start"]
                                streamsid = start["streamSid"]
                                streamsid_queue.put_nowait(streamsid)
                                
                            elif data["event"] == "connected":
                                print("Twilio WebSocket connected")
                                continue
                                
                            elif data["event"] == "media":
                                media = data["media"]
                                chunk = base64.b64decode(media["payload"])
                                if media["track"] == "inbound":
                                    inbuffer.extend(chunk)
                                    print(f"Buffered {len(chunk)} bytes, total buffer: {len(inbuffer)}")
                                    
                            elif data["event"] == "stop":
                                print("Call stopped")
                                break

                            # check if our buffer is ready to send to our audio_queue (and, thus, then to sts)
                            while len(inbuffer) >= BUFFER_SIZE:
                                chunk = inbuffer[:BUFFER_SIZE]
                                audio_queue.put_nowait(chunk)
                                inbuffer = inbuffer[BUFFER_SIZE:]
                                print(f"Sent {len(chunk)} bytes to audio queue")
                                
                        except json.JSONDecodeError as e:
                            print(f"Failed to decode Twilio message: {e}")
                            continue
                        except Exception as e:
                            print(f"Error processing Twilio message: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error in twilio_receiver: {e}")
                finally:
                    print("twilio_receiver ended")
                    # Signal other tasks to stop
                    audio_queue.put_nowait(None)

            # Run all tasks concurrently
            tasks = [
                asyncio.create_task(sts_sender(sts_ws)),
                asyncio.create_task(sts_receiver(sts_ws)),
                asyncio.create_task(twilio_receiver(twilio_ws))
            ]
            
            try:
                # Wait for any task to complete (usually means an error or connection close)
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    
                # Check for exceptions in completed tasks
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        print(f"Task completed with error: {e}")
                        
            except Exception as e:
                print(f"Error in task management: {e}")
            finally:
                # Clean up any remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

            print("Closing Twilio WebSocket")
            try:
                await twilio_ws.close()
            except:
                pass
    except Exception as e:
        print(f"Error in twilio_handler: {e}")
        raise


async def router(websocket):
    print(f"=== ROUTER CALLED ===")
    
    # Get the path from the websocket object
    path = websocket.path if hasattr(websocket, 'path') else "/"
    print(f"Incoming connection on path: {path}")
    print(f"WebSocket object: {websocket}")
    print(f"WebSocket headers: {dict(websocket.request_headers) if hasattr(websocket, 'request_headers') else 'N/A'}")

    try:
        if path == "/twilio" or path == "/":
            # Accept both /twilio and root path for flexibility
            print("Starting Twilio handler")
            await twilio_handler(websocket)
        else:
            print(f"Unknown path: {path}")
            await websocket.close(1008, "Path not found")
    except Exception as e:
        print(f"Error in router: {e}")
        try:
            await websocket.close(1011, "Internal error")
        except:
            pass  # Connection might already be closed

async def main():
    # use this if using ssl
    # ssl_context = ssl.create_default_context(cafile=certifi.where())
    # server = await websockets.serve(router, '0.0.0.0', 443, ssl=ssl_context)

    # use this if not using ssl
    server = await websockets.serve(router, "localhost", 5000)
    print("Server starting on ws://localhost:5000")
    
    # Keep the server running
    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {e}")

        sys.exit(1)
