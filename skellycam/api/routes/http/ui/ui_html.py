UI_HTML_STRING = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <title>SkellyCam API UI Tester</title>
    <style>
        .image {
            width: 640px;
            height: auto;
        }

        div {
            background-color: #654a7b;
        }

        h1 {
            font-size: 24px;
        }

        button {
            margin-right: 10px;
            padding: 10px;
            font-size: small;
        }
    </style>
    <script>
        let ws;
        let isConnected = false;
        const latestImages = {};
        const imageElements = {};

        function updateStatus() {
            document.getElementById('ws-status').innerText = isConnected ? 'Connected' : 'Disconnected';
        }

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8005/websocket/connect');
            
            // websocket helpers
            const decoder = new TextDecoder('utf-8');

            
            ws.onopen = () => {
                isConnected = true;
                updateStatus();
            };
            ws.onclose = () => {
                isConnected = false;
                updateStatus();
            };
            ws.onmessage = async (event) => {
                // Ensure the event.data is a Blob
                if (event.data instanceof Blob) {
                    // Convert the incoming data to an ArrayBuffer
                    const arrayBuffer = await event.data.arrayBuffer();
            
                    // Convert ArrayBuffer to a string
                    const jsonString = decoder.decode(arrayBuffer);
            
                    // Parse the JSON string to a JavaScript object
                    const data = JSON.parse(jsonString);
                    addLogEntry(`Received message with length: ${jsonString.length} from mf_payload# ${data.multi_frame_number}`);
                    console.log(`Received message with length: ${jsonString.length} from mf_payload# ${data.multi_frame_number}`);
            
                    // Now you can use the data object to update your UI
                    updateImages(data.jpeg_images);
                } else {
                    console.error("Received data is not a Blob.");
                }
            };
        }

        function sendMessage(message) {
            if (isConnected) {
                ws.send(message);
            } else {
                alert('WebSocket is not connected.');
            }
        }

        function updateImages(images) {
            const container = document.getElementById('images-container');
            for (const cameraId in images) {
                if (!imageElements[cameraId]) {
                    const imgBox = document.createElement('div');
                    imgBox.className = 'image-box';
                    const img = document.createElement('img');
                    img.className = 'image';
                    imgBox.appendChild(img);
                    container.appendChild(imgBox);
                    imageElements[cameraId] = img;
                }
                if (images[cameraId]) {
                    imageElements[cameraId].src = 'data:image/jpeg;base64,' + images[cameraId];
                }
            }
        }

        function addLogEntry(entry) {
            const logContainer = document.getElementById('log-container');
            const logEntry = document.createElement('div');
            logEntry.innerText = entry;
            logContainer.prepend(logEntry);
        }

        async function callApi(endpoint, method = 'GET') {
            try {
                const response = await fetch(endpoint, {method});
                const data = await response.json();
                document.getElementById('result').innerText = JSON.stringify(data, null, 2);
                addLogEntry(`Success: ${endpoint} - ${JSON.stringify(data)}`);

            } catch (error) {
                document.getElementById('result').innerText = `Error: ${error.message}`;
                addLogEntry(`Error: ${endpoint} - ${error.message}`);
            }
        }
    </script>
</head>
<body>
<!-- Header Section -->
<h1>SkellyCam API Tester with WebSocket</h1>
<p> WebSocket status: <span id="ws-status">Disconnected</span></p>

<!-- WebSocket Section -->
<button onclick="connectWebSocket()">Connect WebSocket</button>
<button onclick="sendMessage('Hello from the client')">Send WS Message</button>

<!-- API Calls Section -->
<!-- Root and App API Calls -->
<button onclick="callApi('http://localhost:8005/')">Read Root</button>
<button onclick="callApi('http://localhost:8005/app/state')">App State</button>
<button onclick="callApi('http://localhost:8005/app/healthcheck')">Hello👋</button>
<button onclick="callApi('http://localhost:8005/app_state/shutdown')">goodbye👋</button>

<!-- Camera Connection API Calls -->
<button onclick="callApi('http://localhost:8005/cameras/connect/apply', 'POST')">Connect/Update Cameras</button>
<button onclick="callApi('http://localhost:8005/cameras/connect')">Connect to Cameras</button>
<button onclick="callApi('http://localhost:8005/cameras/close')">Close Camera Connections</button>

<!-- Camera Operation API Calls -->
<button onclick="callApi('http://localhost:8005/cameras/detect')">Detect Cameras</button>
<button onclick="callApi('http://localhost:8005/cameras/record/start')">Start Recording</button>
<button onclick="callApi('http://localhost:8005/cameras/record/stop')">Stop Recording</button>

<!-- Results and Logs Section -->
<pre id="result"></pre>
<h2>Images</h2>
<div id="images-container"></div>

<h3>Loggs</h2>
<div id="log-container"></div>
</body>
</html>
"""
