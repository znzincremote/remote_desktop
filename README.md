# Run server
cd remote_desktop/backend/src<br>
uvicorn signaling_server:app --reload

# Run desktop app
cd remote_desktop/frontend/src<br>
python ui_screen_cli.py

# Build Instructions for the Frontend Application

This provides instructions to package the **frontend application** (`ui_screen_cli.py`) into an executable using PyInstaller.

---

## Build Command

Use the following command to build the application:

```html
cd remote_desktop/frontend<br>
pyinstaller RemoteDesktop.spec
