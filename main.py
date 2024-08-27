from fastapi.templating import Jinja2Templates
from fastapi import Form, Request, FastAPI, WebSocket
import cv2
import asyncio

from starlette.websockets import WebSocketDisconnect

app = FastAPI()

templates = Jinja2Templates(directory="templates")

desired_width = 640
desired_height = 480

# Dictionary to store the stop_stream_flag for each WebSocket connection
stop_stream_flags = {}
active_clients = {}

class Capture:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = cv2.VideoCapture(rtsp_url)
        self.ac = []
# async def stream_video(websocket: WebSocket, rtsp_url: str):
#     active_clients[rtsp_url] = [websocket]
#     print(active_clients)
#     cap = cv2.VideoCapture(rtsp_url)
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#
#         frame = cv2.resize(frame, (desired_width, desired_height))
#
#         _, buffer = cv2.imencode(".jpg", frame)
#         for ws_obj in active_clients[rtsp_url]:
#             await ws_obj.send_bytes(buffer.tobytes())
#
#     cap.release()


async def stream_video(websocket: WebSocket, rtsp_url: str):
    active_clients[rtsp_url] = [websocket]
    print(active_clients)
    cap = cv2.VideoCapture(rtsp_url)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (desired_width, desired_height))

            _, buffer = cv2.imencode(".jpg", frame)
            for ws_obj in active_clients[rtsp_url]:
                try:
                    await ws_obj.send_bytes(buffer.tobytes())
                except WebSocketDisconnect:
                    active_clients[rtsp_url].remove(ws_obj)

    except Exception as e:
            print(e)
    finally:
        cap.release()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        stop_stream_flags[websocket] = False

        while True:
            print(active_clients)
            message = await websocket.receive_text()
            command, rtsp_url = message.split(":", 1)

            print(command, rtsp_url)
            if command == "start":
                if rtsp_url in active_clients:
                    active_clients[rtsp_url].append(websocket)
                else:
                    asyncio.create_task(stream_video(websocket, rtsp_url))
            elif command == "stop":
                ac = active_clients[rtsp_url]
                if websocket in ac:
                    ac.remove(websocket)

    except Exception as e:
        stop_stream_flags.pop(websocket, None)


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
