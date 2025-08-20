import makeOutboundCall from "./call.js";
import express from "express";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 9000;

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cors());

// Routes
app.post("/api/calls", async (req, res) => {
  const { to } = req.body;

  // Validate phone number
  if (!to) {
    return res.status(400).json({
      error: "Phone number is required",
      message: "Please provide a 'to' field with the phone number",
    });
  }

  try {
    console.log(`Initiating call to: ${to}`);
    const callSid = await makeOutboundCall(to);

    res.status(200).json({
      success: true,
      message: "Call initiated successfully",
      callSid: callSid,
      to: to,
    });
  } catch (error) {
    console.error("Error initiating call:", error);
    res.status(500).json({
      success: false,
      error: "Error initiating call",
      details: error.message,
    });
  }
});

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.status(200).json({
    status: "healthy",
    message: "Call API is running",
    timestamp: new Date().toISOString(),
  });
});

// Root endpoint
app.get("/", (req, res) => {
  res.json({
    message: "Twilio Call API",
    endpoints: {
      "POST /api/calls": "Initiate an outbound call",
      "GET /api/health": "Health check",
    },
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Call API Server is running on port ${PORT}`);
  console.log(`📞 POST http://localhost:${PORT}/api/calls to make calls`);
  console.log(`💚 GET http://localhost:${PORT}/api/health for health check`);
});
