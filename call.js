import twilio from "twilio";

const ACCOUNT_SID = "AC59b187f6e2ed73cebc6f8025af1058af";
const AUTH_TOKEN = "28a1c9b3c3ee3faf02447d1c7f947d42";
const FROM_NUMBER = "+18154291999";
const TO_NUMBER = "+918700407283";

const twilioClient = twilio(ACCOUNT_SID, AUTH_TOKEN);

const twiml = `
<Response>
    <Say>Connecting to the call...</Say>
    <Connect>
        <Stream url="wss://internal-completely-jobs-printed.trycloudflare.com/twilio" />
    </Connect>
</Response>
`;

export default async function makeOutboundCall(to_number) {
  const call = await twilioClient.calls.create({
    to: to_number,
    from: FROM_NUMBER,
    twiml: twiml,
  });
  console.log("Call SID:", call.sid);
  return call.sid; // Return the call SID for API response
}

// Remove the immediate call - only call when imported
// makeOutboundCall();
