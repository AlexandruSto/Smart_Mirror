import io
import time
import picamera
import logging
import socketserver
from threading import Condition
from http import server
from google.cloud import vision
from google.cloud.vision_v1 import types
from google.oauth2 import service_account

# Constants
credentials = service_account.Credentials.from_service_account_file('/home/pdemotion/Desktop/ui/ServiceAccountToken.json')

client = vision.ImageAnnotatorClient(credentials=credentials)

EMOTION_RANGE = ["joy_likelihood", "sorrow_likelihood", "anger_likelihood"]

# This Class handles the output from Picamera.
class StreamingOutput(object):
    def _init_(self):
        self.frame = None
        self.last_frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.last_frame = self.frame
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

# This Class handles client actions and responses sent by the server.
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            with open('index.html', 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/ScanIcon.png':
            with open('ScanIcon.png', 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            # Handle Video feed display, emulating 'true mirror' behaviour
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        elif self.path == '/centre':
            # Handle centre button click event
            self.send_response(200)
            time.sleep(1)
            emotion = None
            # Store last frame to send for emotion recognition
            frame = output.last_frame
            if frame:
                image = types.Image(content=frame)
                response = client.face_detection(image=image)

                # Analize response 
                face_annotations = response.face_annotations
                for _, face in enumerate(face_annotations):
                    max_likelihood = types.Likelihood.POSSIBLE
                    for attr in EMOTION_RANGE:
                        likelihood = getattr(face, attr)
                        if likelihood > max_likelihood:
                            max_likelihood = likelihood
                            emotion = attr.split("_")[0].title()
            else:
                logging.warning("Could not acces a valid frame")

            # Send emotion to the webpage
            if emotion is None:
                emotion = "No emotion"
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(emotion.encode('utf-8'))
        elif self.path == '/center':
            # Handle center button click event
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Center button pressed')
        elif self.path == '/right':
            # Handle right button click event
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Right button pressed')
        else:
            self.send_error(404)
            self.end_headers()

# Streaming server instance used for hosting
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# Get video feed from the camera and send it to the html page
with picamera.PiCamera(resolution='640x480', framerate=32) as camera:
    output = StreamingOutput()
    #Uncomment the next line to change your Pi's Camera rotation (in degrees)
    #camera.rotation = 90
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
        camera.close()
