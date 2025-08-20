import WebSocket from "ws";
import { createServer } from "http";
import { createClient } from "@deepgram/sdk";
import { CartesiaClient } from "@cartesia/cartesia-js";
import fetch from "node-fetch";

const DEEPGRAM_API_KEY = "68ea08e124b23d0ce4712297b91237e9b89799bb";
const CARTESIA_API_KEY = "sk_car_cdsHpmGRasBLNfd62zRJEs";
const OPENAI_API_KEY =
  "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";

const SYSTEM_PROMPT =
  "You are Steve, a friendly AI agent making a phone call...";

const deepgram = createClient(DEEPGRAM_API_KEY);
const cartesia = new CartesiaClient({ apiKey: CARTESIA_API_KEY });

let conversationContext = {
  messages: [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "assistant", content: "Hi there!..." },
  ],
  callSid: null,
  isProcessing: false,
};

async function getAIResponse(userMessage) {
  conversationContext.messages.push({ role: "user", content: userMessage });
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: conversationContext.messages,
      max_tokens: 150,
      temperature: 0.7,
    }),
  });
  const data = await response.json();
  console.log(data);
  const aiResponse = data.choices[0].message.content;
  conversationContext.messages.push({ role: "assistant", content: aiResponse });
  return aiResponse;
}

async function generateSpeechFromAI(aiResponse) {
  const resp = await cartesia.tts.bytes({
    modelId: "sonic-2",
    transcript: aiResponse,
    voice: { mode: "id", id: "694f9389-aac1-45b6-b726-9d9369183238" },
    language: "en",
    outputFormat: {
      container: "raw",
      sampleRate: 8000,
      encoding: "pcm_mulaw",
    },
  });
  console.log(resp);
  return resp;
}

async function sendAudioToTwilio(ws, audioData) {
  const chunkSize = 160;
  for (let i = 0; i < audioData.length; i += chunkSize) {
    const chunk = audioData.slice(i, i + chunkSize);
    const b64 = chunk.toString("base64");
    const mediaMessage = {
      event: "media",
      streamSid: conversationContext.callSid,
      media: { payload: b64 },
    };
    ws.send(JSON.stringify(mediaMessage));
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}

const server = createServer();
const wss = new WebSocket.Server({ server });

wss.on("connection", (ws) => {
  console.log("New WebSocket connection established");
  let deepgramSocket = null;
  const deepgramUrl = `wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&model=nova-2&language=en&smart_format=true&punctuate=true&interim_results=false`;

  deepgramSocket = new WebSocket(deepgramUrl, {
    headers: { Authorization: `Token ${DEEPGRAM_API_KEY}` },
  });
  console.log("Deepgram WebSocket connection established");

  deepgramSocket.on("message", async (data) => {
    console.log("Deepgram WebSocket message received");
    const transcript = JSON.parse(data);
    if (transcript.channel?.alternatives?.[0]?.transcript) {
      const userMessage = transcript.channel.alternatives[0].transcript;
      if (userMessage.trim() && !conversationContext.isProcessing) {
        conversationContext.isProcessing = true;
        try {
          const aiResponse = await getAIResponse(userMessage);
          const audioData = await generateSpeechFromAI(aiResponse);
          await sendAudioToTwilio(ws, audioData);
        } catch (e) {
        } finally {
          conversationContext.isProcessing = false;
        }
      }
    }
  });

  ws.on("message", async (message) => {
    const msg = JSON.parse(message);
    console.log("Twilio WebSocket message received");
    switch (msg.event) {
      case "connected":
        setTimeout(async () => {
          const greeting = conversationContext.messages[1].content;
          const audioData = await generateSpeechFromAI(greeting);
          await sendAudioToTwilio(ws, audioData);
        }, 1000);
        break;
      case "media":
        if (deepgramSocket && deepgramSocket.readyState === WebSocket.OPEN) {
          const audioChunk = Buffer.from(msg.media.payload, "base64");
          deepgramSocket.send(audioChunk);
        }
        break;
      case "stop":
        deepgramSocket.close();
        break;
    }
  });
  ws.on("close", () => {
    if (deepgramSocket) deepgramSocket.close();
  });
});

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log("WebSocket server listening on port", PORT);
});
