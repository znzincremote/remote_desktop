from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
import asyncio
from aiortc.contrib.signaling import BYE, object_from_string, object_to_string
from utils.utils import InMemoryStore, ScreenShareTrack
from utils.websocket_handler import WebSocketClient
from config import SIGNALING_SERVER
import json
import traceback
import pyautogui
import tkinter as tk

pyautogui.FAILSAFE = False
class WebRTCHandler:
    def __init__(self, **kwargs):
        self.loop = asyncio.new_event_loop()
        self.inmemory_store = InMemoryStore()
        self.system_hardware_info = kwargs["get_system_hardware_info"]()
        self.perform_local_system_connection_successs = kwargs["perform_local_system_connection_successs"]
        self.perform_remote_system_connection_successs = kwargs["perform_remote_system_connection_successs"]
        self.close_accessing = kwargs["close_accessing"]
        self.show_message = kwargs["show_message"]
        self.initialize_realtime_app(kwargs=kwargs)
        self.show_image = kwargs["show_image"]
        self.bind_system_events = kwargs["bind_system_events"]
        self.root = kwargs["root"]
        self.placeholder = kwargs["placeholder"]
        self.perform_event = kwargs["perform_event"]
        self.handle_connection_request = kwargs["handle_connection_request"]
        self.target_client_id = None
        self.remote_system_width = None
        self.remote_system_height = None
        self.system_info = None
        self.remote_system_answer_status = "pending"

        @self.pc.on("track")
        def on_track(track):
            if track.kind == "video":
                self.start_track_async(track)

    def initialize_realtime_app(self, kwargs):
        """ 
            - Intitialize the WebSocket connection
            - Intitialize RealTimeCommunication Peer connection
        """
        websocket_conf = {
            "signaling_server": f"{SIGNALING_SERVER}/{self.system_hardware_info['unique_system_id']}", 
            "inmemory_store": self.inmemory_store,
            "process_websocket_status": kwargs["process_websocket_status"], 
            "show_message": kwargs["show_message"],
            "handle_start_button": kwargs["handle_start_button"]
        }
        self.ws = WebSocketClient(**websocket_conf)
        self.chat_channel = None
        self.pc = RTCPeerConnection()

    async def receive(self):
        while not self.inmemory_store.incoming:
            await asyncio.sleep(0.1)
        return object_from_string(self.inmemory_store.incoming.pop(0))

    async def send(self, descr):
        self.inmemory_store.outgoing.append(json.loads(object_to_string(descr)))

    def channel_send(self, channel, message):
        if channel.readyState=="open":
            channel.send(message)
        elif channel.readyState=="closed":
            ...
            #TODO: I'll add a red circle icon in the UI to indicate that the connection is closed
        else:
            print(f"<<<<<<<<<<Channel is in {channel.readyState} state.>>>>>>>>>>")
    
    async def chat_channel_send(self, message):
        if self.chat_channel:
            self.channel_send(self.chat_channel, message)
    
    async def run_answer(self):
        print("Inside answer run")
        self.system_info = "remote_system"
        self.perform_remote_system_connection_successs()
        print("perform_remote_system_connection_successs performed")
        try:
            screen_track = ScreenShareTrack()
            print("Scren_track ====", screen_track)
            self.pc.addTrack(screen_track)
            print("Track added")
            async def on_datachannel(channel):
                print("Datachannle created ------")
                self.chat_channel = channel
                print("self.chat_channel ============", self.chat_channel)

                @self.chat_channel.on("message")
                def on_message(message):
                    print("<<<<<<<<<<<<<<<<<<<<<<<<<< ANSWER Message ===============", message)
                    try:
                        message = json.loads(message)

                        if message.get("ping") and not message.get("type") == "force_close_connection":
                            try:
                                # Perform the event send from local system event
                                ping = message["ping"]
                                self.perform_event(ping)
                            except Exception as e:
                                pass
                        elif message.get("type") == "force_close_connection":
                            self.close_accessing(message=message.get("ping"))
                        elif message.get("remote_details") is True:
                            asyncio.run_coroutine_threadsafe(self.chat_channel_send(json.dumps({
                                "remote_details": True,
                                "remote_system_width": self.root.winfo_screenwidth(),
                                "remote_system_height": self.root.winfo_screenheight()
                            })), self.loop)
                    except Exception as e:
                        pass

                @self.chat_channel.on("close")
                def on_close():
                    print("<<<<<<<<<<<<<<<<<<<<<<<< Closed on remote system >>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    asyncio.run_coroutine_threadsafe(
                        self.chat_channel_send(json.dumps({
                            "connectivity": False,
                            "type": "force_close_connection",
                            "pong": "Connection closed by remote system"
                        }))
                        , self.loop
                    )
                    print("Let's send the close connection message to local system")

            self.pc.on("datachannel", on_datachannel)
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            await self.send(self.pc.localDescription)
        except Exception as e:
            error_message = traceback.format_exc()
            error_lines = error_message.splitlines()
            traceback.print_exc()
            print(f"Exception occured inside Answer : {e}")

    async def run_offer(self):
        self.bind_system_events(self.placeholder, self.root)  # Events capturing for local system only
        self.system_info = "local_system"
        try:
            screen_track = ScreenShareTrack(blank_screen=True)
            self.pc.addTrack(screen_track)
            self.chat_channel = self.pc.createDataChannel("chat")

            @self.chat_channel.on("open")
            def on_open():
                print("Chat channel is opened")
                # Get remote screen size by sending message to remote device
                self.perform_local_system_connection_successs()
                asyncio.run_coroutine_threadsafe(self.chat_channel_send(json.dumps({"remote_details": True})), self.loop)

            @self.chat_channel.on("message")
            def on_message(message):
                print("<<<<<<<<<<<<<<<<<<<<<<<< OFFER MESSAGE =================", message)
                try:
                    message = json.loads(message)
                    if message.get("pong") and not message.get("type") == "force_close_connection":
                        try:
                            pong = message.get("pong")
                            self.perform_event(pong)
                        except Exception as e:
                            pass
                    elif message.get("type") == "force_close_connection":
                        self.close_accessing(message=message.get("pong"))
                    elif message.get("remote_details") is True:
                        # Set remote screen size
                        self.remote_system_width, self.remote_system_height = message["remote_system_width"], message["remote_system_height"]
                except Exception as e:
                    pass

            @self.chat_channel.on("close")
            def on_close():
                self.channel_send(json.dumps({
                    "connectivity": False,
                    "type": "force_close_connection",
                    "ping": None
                }))
                print("<<<<<<<<<<<<<<<<<<<<<<<< Closed on local system >>>>>>>>>>>>>>>>>>>>>>>>>>>")

            offer = await self.pc.createOffer()

            await self.pc.setLocalDescription(offer)

            # Sending the local description (offer) to the other peer
            await self.send(self.pc.localDescription)

        except Exception as e:
            error_message = traceback.format_exc()
            error_lines = error_message.splitlines()
            traceback.print_exc()


    async def consume_signaling(self):
        while True:
            obj = await self.receive()
            print("obj inside consume_signaling ==========", obj)
            if isinstance(obj, RTCSessionDescription):
                await self.pc.setRemoteDescription(obj)
                if obj.type == "offer":
                    answer_status = self.handle_connection_request()
                    print("answer_status =======", answer_status)
                    if answer_status:
                        await self.run_answer()
                    elif answer_status == False:
                        self.show_message(title="Remote Client rejected connection", type="INFO", message="Remote system rejected the connection !")
            elif isinstance(obj, RTCIceCandidate):
                await self.pc.addIceCandidate(obj)
            elif obj is BYE:
                break

    async def send_message_worker(self):
        while True:
            if self.inmemory_store.outgoing:
                await self.ws.send_message(self.inmemory_store.outgoing.pop(0))
            await asyncio.sleep(0.1)

    async def ws_async(self):
        await self.ws.connect()
        await asyncio.gather(self.ws.listen(), self.send_message_worker(), self.consume_signaling())

    async def webrtc_async(self):
        self.ws.target_client_id = self.target_client_id
        await self.run_offer()

    def start_webrtc_connection(self):
        asyncio.run_coroutine_threadsafe(self.webrtc_async(), self.loop)

    def close_webrtc_connection(self):
        """ Close the webrtc connection, tracks (Sent, Received) """
        # try:
        if self.chat_channel and self.chat_channel.readyState == "open":
            self.chat_channel.close()
            print("Data channel closed.")

        # Stop all media tracks being sent
        for sender in self.pc.getSenders():
            track = sender.track
            if track:
                track.stop()

        # Stop all media tracks being received
        for receiver in self.pc.getReceivers():
            track = receiver.track
            if track:
                track.stop()
                print(f"Stopped receiving track: {track.kind}")

        # Close the RTCPeerConnection
        asyncio.run_coroutine_threadsafe(self.pc.close(), self.loop)

        # Reset WebRTC-related attributes for a clean state
        self.chat_channel = None
        self.remote_system_width = None
        self.remote_system_height = None
        self.remote_system_answer_status = "pending"


    def start_web_socket_connection(self):
        asyncio.run_coroutine_threadsafe(self.ws_async(), self.loop)

    async def display_video(self, track):
        while True:
            frame = await track.recv()
            img = frame.to_ndarray(format="bgr24")
            self.show_image(img)

    async def track_async(self, track):
        await self.display_video(track)

    def start_track_async(self, track):
        asyncio.run_coroutine_threadsafe(self.track_async(track), self.loop)

