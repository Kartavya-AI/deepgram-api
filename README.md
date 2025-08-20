### Run `server.py`, expose via Cloudflare Tunnel, and place a call with `call.js`

#### 1) Run `server.py`
```bash
cd test
python3 -m pip install websockets certifi
python3 server.py
```

#### 2) Make a tunnel with Cloudflare Tunnel
```bash
# macOS install (once)
brew install cloudflared

# start a public tunnel to your local server on port 5000
cloudflared tunnel --url http://localhost:5000
```

#### 3) Connect the tunnel to localhost:5000
- The command above already connects the tunnel to `localhost:5000`.
- Copy the public URL shown by `cloudflared` and use it in `call.js` as:
```xml
<Stream url="wss://<your-subdomain>.trycloudflare.com/twilio" />
```

#### 4) Run `call.js` (it will call the number specified)
```bash
cd test
npm install
node call.js
```


