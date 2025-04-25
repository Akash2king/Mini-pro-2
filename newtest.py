from flask import Flask, request, render_template, url_for
import logging, os, time, base64, requests
from gtts import gTTS
from datetime import datetime

app = Flask(__name__)

IMAGE_PATH = os.path.join(app.root_path, "static/test.jpg")
AUDIO_PATH = os.path.join(app.root_path, "static/audio.mp3")
DESCRIPTION = ""
LAST_IMAGE_TIMESTAMP = ""

logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    logging.info('Headers: %s', request.headers)
    logging.info('Body: %s', request.get_data())

@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    global DESCRIPTION, LAST_IMAGE_TIMESTAMP

    if request.method == "POST":
        image_raw_bytes = request.get_data()
        with open(IMAGE_PATH, 'wb') as f:
            f.write(image_raw_bytes)
        print("Image saved")

        with open(IMAGE_PATH, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        gemini_response = get_image_description(img_base64)
        DESCRIPTION = gemini_response or "Could not generate description."

        tts = gTTS(text=DESCRIPTION, lang='en')
        tts.save(AUDIO_PATH)

        LAST_IMAGE_TIMESTAMP = str(datetime.utcnow().timestamp())

        return "Image and description processed."

    elif request.method == "GET":
        return render_template("image_show.html", 
                               description=DESCRIPTION, 
                               timestamp=LAST_IMAGE_TIMESTAMP)

def get_image_description(base64_image):
    API_KEY = "AIzaSyB4GgtY8Tkf6KeCx9CbkDykvSviN_bkmAg"  # Replace this with your valid API Key
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": base64_image
                    }
                },
                {
                    "text": '''
I am a blind individual, and I would like you to assist me in understanding images by providing detailed, vivid, and sensory-rich descriptions. 
Describe spatial layout, visual details, sensory cues, context, and key focal points as if I were experiencing the scene naturally.
'''
                }
            ]
        }]
    }

    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(endpoint, json=payload, headers=headers)
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", e)
        print("Full response:", res.text if 'res' in locals() else "No response")
        return None

if __name__ == '__main__':
    from flask_cors import CORS
    CORS(app)  # Allow all origins
    app.run(host='0.0.0.0', port=5000)
