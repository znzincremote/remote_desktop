import asyncio
import json
import websockets
from config import RECONNECTION_DELAY

class WebSocketClient:
    """Class to manage WebSocket connection and event handling."""

    def __init__(self, **kwargs):
        self.signaling_server = kwargs["signaling_server"]
        self.inmemory_store = kwargs["inmemory_store"]
        self.process_websocket_status = kwargs["process_websocket_status"]
        self.show_message = kwargs["show_message"]
        self.handle_start_button = kwargs["handle_start_button"]
        self.websocket = None
        self.client_id = None
        self.target_client_id = None

    async def connect(self):
        # TODO """Connect to the WebSocket server and handle reconnection logic."""
        """Connect to the WebSocket server """
        try:
            # Attempt to connect to the WebSocket server
            self.websocket = await websockets.connect(self.signaling_server)
            print("Connected to WebSocket.")
            self.process_websocket_status(status=True)
            # Trigger on_open listener
            self.on_open()

        except Exception as e:
            # Trigger on_error listener
            self.on_error(e)
            print(f"Failed to connect to WebSocket: {e}. Retrying in {RECONNECTION_DELAY} seconds...")
            await asyncio.sleep(RECONNECTION_DELAY)

    async def listen(self):
        """Listen for incoming messages and handle them."""
        try:
            async for message in self.websocket:
                await self.on_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed. Reconnecting...")
            print(f"WebSocket connection error : {websockets.exceptions.ConnectionClosed}")
            print(f"WebSocket connection error code : {websockets.exceptions.ConnectionClosed.code}")
            print(f"WebSocket connection error reason : {websockets.exceptions.ConnectionClosed.reason}")
    
    async def send_message(self, message):
        """Send a message through the WebSocket."""
        if self.websocket and self.target_client_id:
            await self.websocket.send(json.dumps({"target_client_id": self.target_client_id, "message": message}))
        else:
            print("WebSocket is not connected or target client ID is not set.")

    # WebSocket Event Listeners

    def on_open(self):
        """Event triggered when WebSocket connection is opened."""
        print("WebSocket connection opened.")

    async def on_message(self, message):
        """Event triggered when a message is received from WebSocket."""
        print(f"Received message: {message}")

        # Example: Extract client ID from the first message
        try:
            data = json.loads(message)
            if data.get("status") == "TARGET_NOT_AVAILABLE":
                self.show_message(title="Client offline", type="ERROR", message="Client with this address is not availble.")
                self.handle_start_button(state="normal", text="Start", cursor="hand2")
            if 'client_id' in data:
                self.client_id = data['client_id']
                print(f"Client ID set to: {self.client_id}")
            if 'from_client_id' in data:
                self.target_client_id = data['from_client_id']
                print(f"Target client ID set to: {self.target_client_id}")

            json_data = data.get("message", {})
            if json_data:
                self.inmemory_store.incoming.append(json.dumps(json_data))
        
        except json.JSONDecodeError:
            print("Failed to decode message as JSON.")

    def on_error(self, error):
        """Event triggered when an error occurs."""
        print(f"WebSocket error: {error}")

    def on_close(self):
        """Event triggered when WebSocket connection is closed."""
        self.process_websocket_status(status=False)
        print("WebSocket connection closed.")
