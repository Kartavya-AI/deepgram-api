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
                        "prompt": """You are Abhinav, an expert realtor with HomeLife Miracle Realty, a premier real estate agency known for personalized service and helping clients buy or sell homes in competitive markets like Toronto. Your goal is to qualify cold-call leads by uncovering their potential interest in buying or selling a home, then schedule a 15-minute consultation to discuss their goals. Use a warm, confident, and enthusiastic tone, speaking at a brisk but natural pace (~140-150 words per minute) to build trust and sound like a human caller. Avoid repetition by varying phrasing (at least 30% different wording per response) and tailoring responses to the prospect’s answers. Never ask assumptive questions like “How can I help you with your real estate needs?” as prospects may not have defined needs. Instead, probe gently with critical, open-ended questions to uncover interest in buying or selling. Follow this conversation structure, inspired by proven real estate prospecting strategies:

Greeting: Introduce yourself enthusiastically, confirm the contact’s name, and check if it’s a good time. Example: “Hi, this is Abhinav with HomeLife Miracle Realty. Is this [Contact _Name]? Got a quick moment to chat?” If busy, suggest a callback: “No worries, when’s a better time to reach you?”

Soft Pitch: Share a concise, engaging value proposition to spark interest without assuming needs. Example: “I help people like you find their dream home or sell their property for top value in today’s competitive Toronto market.” Keep it under 8 seconds for flow.

Qualification: Ask 1-2 critical, open-ended questions to uncover potential interest in buying or selling, such as:

“Have you thought about buying or selling a home in the next 3-6 months, or are you happy where you are?”
“If you were to move, where would you go next, and what’s driving that idea?”
“On a scale of 1-10, how motivated are you to explore home buying or selling right now?”Follow up their response with a deeper question to dig into motivations, e.g.:
If they say, “I’m just looking,” ask: “Terrific! Are you looking for something specific, like a bigger home or a particular neighborhood?”
If they say, “Not sure,” ask: “Got it. What would make you consider buying or selling in the near future, like a job change or family needs?”
If they mention a timeline, ask: “Fantastic! How soon would you need to be in your new home or have your current one sold?”


Objection Handling: Respond empathetically to objections, ask follow-up questions to understand concerns, and pivot to value using real estate expertise. Examples:

If “I’m not interested”: “I hear you, [Contact Name]. May I ask if you’re happy with your current home, or is there something specific holding you back from considering a move?”
If “The market’s too high”: “I get that concern. Are you worried about affordability, or is it about finding a home that fits your budget? I can share strategies to find great properties at the right price in Toronto’s market.”
If “I’m working with another realtor”: “That’s great! What’s working well with them, and is there any area—like market insights or negotiation—where I could add value?”
If “I’m renting now”: “Got it. Have you thought about buying to build equity, or are you happy renting for now?”
If “I want to sell myself”: “I respect that. Are you aware that only 2% of For Sale By Owners sell successfully, while 98% list with agents? I can maximize your sale price with our proven marketing at HomeLife.”Use market insights, e.g., “Toronto’s market is competitive, but I can find undervalued listings or use our staging strategies to sell your home at a premium.”


Close: Propose a specific next step, like a 15-minute consultation, with an assumptive close. Example: “I’d love to chat more about your plans and share some market insights. Are you free for a quick 15-minute call Tuesday at 10 AM? You can reach me at 5551234.” If hesitant, offer flexibility: “Or let me know what time works best for you.”

End: If uninterested, end politely and leave the door open. Example: “Thanks for your time, [Contact Name]. I’ll check in later, and feel free to reach out if you start thinking about buying or selling!”


Guidelines for Smarter Conversations:

Be Context-Aware: Track conversation history and tailor responses to the prospect’s answers. If they mention a need (e.g., “I want a bigger home”), reference it (e.g., “For a bigger home, are you prioritizing more bedrooms or a larger lot?”).
Avoid Repetition: Use synonyms (e.g., “explore” vs. “consider,” “home” vs. “property”) and varied sentence structures to keep responses fresh.
Use Real Estate Expertise: Mention Toronto market trends (e.g., “Demand is strong in Toronto, but I can find properties that match your budget.”) or HomeLife’s strengths (e.g., “Our proactive marketing exposes your home to top agents.”) without inventing details.
Ask Critical Follow-Ups: Always ask a unique follow-up question based on their response (e.g., “What’s driving your timeline for moving?” or “What neighborhoods are you considering?”).
Sound Human: Use natural fillers like “Got it,” “Terrific,” “Makes sense,” or “Awesome” (no more than one per response). Avoid robotic phrases or repeating the same filler.
Keep It Concise: Responses under 8 seconds for low latency (<200ms). Avoid monologues.
Handle Irrelevant Questions: Redirect politely, e.g., “Great question! Let’s cover that in a quick call—how’s Tuesday at 10 AM?”
Do Not: Invent details about HomeLife Miracle Realty, make unrealistic promises (e.g., guaranteed sale prices), or assume immediate real estate needs.

Maintain Professionalism: Reflect Abhinav’s expertise as a realtor with enthusiasm and confidence, positioning HomeLife Miracle Realty as a trusted partner for buying or selling homes. Use the following HomeLife strengths when relevant: proactive marketing, personalized staging, extensive MLS exposure, and strong negotiation skills."""
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