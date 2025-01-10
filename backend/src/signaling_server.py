import json
import os
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Path, status, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from db_conf import get_db
from models import SystemInfo, User
from route_models import SystemInfoRequest, LoginRequest, RegisterRequest
from utils.system_address_conf import get_address
from utils.auth_utilities import create_access_token, current_user, api_key_required
from utils.routes_utilities import validate_user


API_KEY = os.environ["API_KEY"]

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket : WebSocket, db : Session, unique_id : str):
        await websocket.accept()
        remote_desktop_address = db.query(SystemInfo).filter(SystemInfo.unique_system_id == unique_id).first().remote_desktop_address
        self.active_connections[remote_desktop_address] = websocket
        await websocket.send_text(json.dumps({"client_id": remote_desktop_address}))
        return remote_desktop_address

    def disconnect(self, client_id: int):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, recipient_id: int, sender_id: int):
        if recipient_id in self.active_connections:
            connection = self.active_connections[recipient_id]
            await connection.send_text(message)
        else:
            # If the target client is not available, notify the sender
            sender_connection = self.active_connections.get(sender_id)
            if sender_connection:
                await sender_connection.send_text(json.dumps({"status": "TARGET_NOT_AVAILABLE"}))

# Instantiate connection manager
manager = ConnectionManager()

# WebSocket endpoint for signaling
@app.websocket("/ws/{unique_id}")
async def websocket_endpoint(websocket: WebSocket, unique_id: str = Path(..., description="The unique system ID"), db: Session = Depends(get_db)):
    client_id = await manager.connect(websocket, db, unique_id)
    try:
        while True:
            # Receive data in JSON format from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Expect data to have a target_client_id and message
            target_client_id = message_data.get("target_client_id")
            message = message_data.get("message")

            if target_client_id and message:
                # Send message to the target client, or notify sender if unavailable
                await manager.send_message(json.dumps({"from_client_id": client_id, "message": message}), target_client_id, client_id)
            else:
                print("Invalid message format:", message_data)
                await websocket.close(code=1003, reason="Invalid message format")
                manager.disconnect(client_id)
                break

    except WebSocketDisconnect:
        # Disconnect client on WebSocket disconnection
        manager.disconnect(client_id)


# ------------------------------------ Authentication Routes ---------------------------------------
@app.post("/check-authentication", dependencies=[Depends(api_key_required)])
async def check_authentication(current_user: dict = Depends(current_user)):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": True, "message": "User is authenticated.", "user": current_user}
    )


@app.post('/login', dependencies=[Depends(api_key_required)])
async def login(request_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request_data.username).first()
    if user:
        if user.check_password(request_data.password):
            # Generate the JWT token after successful login
            access_token = create_access_token(data={"sub": user.username})
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": True, "user_id": user.id, "message": "Login successful", "access_token": access_token}
            ) 
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": False, "message": "Invalid password.Please try again."}
            )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": False, "message": "Invalid username. Do you registered yet?"}
    )


@app.post('/register', dependencies=[Depends(api_key_required)])
async def register(request_data: RegisterRequest, db: Session = Depends(get_db)):
    data=request_data.model_dump()
    user_validation = validate_user(data=data, db=db)
    if user_validation.get("status") is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": False, "message": user_validation.get("message")}
        )
    user = User().create_user(db, data)
    if user:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status": True, "user_id": user.id, "message": "User registered successfully."}
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": False, "message": "Failed to create user. Please try again later."}
    )

# ---------------------------------------- User-System Features Routes -------------------------------------------

@app.post('/system-info', dependencies=[Depends(api_key_required), Depends(current_user)])
async def current_system_info(request_data: SystemInfoRequest, db: Session = Depends(get_db)):
    """ Get or create system address when user start application """
    system_data = {
        "operating_system": request_data.operating_system,
        "unique_system_id": request_data.unique_system_id
    }

    address = get_address(db, unique_system_id=system_data["unique_system_id"], data=system_data)
    print(f"System address : {address}")
    return {"status": True, "remote_id": address}


# ------------------------------------------- web pages ----------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request : Request):
    return templates.TemplateResponse("main_pages/index.html", {"request": request})


@app.get("/remote-desktop/download", response_class=HTMLResponse)
def remote_desktop_download(request : Request):
    return templates.TemplateResponse("download_pages/download_page.html", {"request": request})


# ------------------------ Download exe file routes -----------------------
@app.get("/remote-desktop/download/{os_type}/v_{version}")
async def download_executable(os_type: str, version : str):
    requested_version = f"v_{version}"
    if os_type.lower() == "windows":
        file_path = os.path.join("static", "app_files", "Windows", requested_version, "RemoteDesktop.exe")
        filename = "RemoteDesktop.exe"
    elif os_type.lower() == "linux":
        file_path = os.path.join("static", "app_files", "Linux", requested_version, "RemoteDesktop")
        filename = "RemoteDesktop"
    else:
        return {"error": "Unsupported OS type"}
    
    print(file_path)

    # Check if the file exists and return the response
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/octet-stream', filename=filename)
    else:
        return {"error": "File not found"}