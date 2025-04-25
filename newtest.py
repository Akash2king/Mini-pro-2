from flask import Flask, request, render_template, url_for
import logging, os, time, base64, requests
from gtts import gTTS
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all origins

IMAGE_PATH = os.path.join(app.root_path, "static/test.jpg")
AUDIO_PATH = os.path.join(app.root_path, "static/audio.mp3")
DESCRIPTION = ""

logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    logging.info('Headers: %s', request.headers)
    logging.info('Body: %s', request.get_data())

@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    global DESCRIPTION

    if request.method == "POST":
        image_raw_bytes = request.get_data()
        with open(IMAGE_PATH, 'wb') as f:
            f.write(image_raw_bytes)
        print("Image saved")

        # Call Gemini Flash for description
        with open(IMAGE_PATH, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        gemini_response = get_image_description(img_base64)
        DESCRIPTION = gemini_response or "Could not generate description."

        # Generate TTS
        tts = gTTS(text=DESCRIPTION, lang='en')
        tts.save(AUDIO_PATH)

        return "Image and description processed."

    elif request.method == "GET":
        return render_template("image_show.html", description=DESCRIPTION, timestamp=str(time.time()))

def get_image_description(base64_image):
    API_KEY ="AIzaSyB4GgtY8Tkf6KeCx9CbkDykvSviN_bkmAg"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={API_KEY}"
    
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
                    "text":  '''
"I am a blind individual, and I would like you to assist me in understanding images by providing detailed, vivid, and sensory-rich descriptions. When I upload an image, please describe it as though you are guiding me through the scene in a natural and immersive way. Your description should include:

1. Spatial Layout: Describe the arrangement of objects, people, or elements in the scene, including approximate distances.
2. Visual Details: Mention colors, shapes, sizes, and textures.
3. Sensory Cues: Include implied sounds, smells, or tactile sensations.
4. Context and Atmosphere: Provide context about the setting, mood, or activity.
5. Key Focal Points: Highlight the most important or prominent elements and their relationships.

Your goal is to help me visualize the scene as if I were experiencing it myself, with clarity, detail, and natural flow. Avoid phrases like 'let me explain' or 'in the image'; simply describe the scene directly and vividly."
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
        print(f"Gemini error: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
