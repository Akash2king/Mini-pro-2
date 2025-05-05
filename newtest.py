from flask import Flask, request, render_template, jsonify
import os, time, base64, requests, uuid
from gtts import gTTS
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "static")
DESCRIPTION = ""
CURRENT_IMAGE = None
CURRENT_AUDIO = None

@app.route("/upload-image", methods=["POST"])
def upload_image():
    global DESCRIPTION, CURRENT_IMAGE, CURRENT_AUDIO

    # Cleanup old files
    if CURRENT_IMAGE:
        try: os.remove(CURRENT_IMAGE)
        except: pass
    if CURRENT_AUDIO:
        try: os.remove(CURRENT_AUDIO)
        except: pass

    # Generate unique ID
    unique_id = str(uuid.uuid4())
    image_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.jpg")
    audio_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}.mp3")

    # Save image
    image_raw_bytes = request.get_data()
    with open(image_path, 'wb') as f:
        f.write(image_raw_bytes)
    CURRENT_IMAGE = image_path
    CURRENT_AUDIO = audio_path

    print(f"[INFO] Image saved as: {image_path}")

    # Call Gemini for description
    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

    gemini_response = get_image_description(img_base64)
    DESCRIPTION = gemini_response or "Could not generate description."
    print(f"[INFO] Description: {DESCRIPTION}")

    # Generate audio
    tts = gTTS(text=DESCRIPTION, lang='en')
    tts.save(audio_path)
    print(f"[INFO] Audio saved as: {audio_path}")

    return {"status": "done", "id": unique_id}

@app.route("/view", methods=["GET"])
def view():
    return render_template("image_show.html", description=DESCRIPTION, timestamp=str(time.time()))

@app.route("/latest-id", methods=["GET"])
def get_latest_id():
    if CURRENT_IMAGE:
        filename = os.path.basename(CURRENT_IMAGE).split(".")[0]
        return {"id": filename}
    return {"id": None}

# In-memory storage for latest GPS and ultrasonic readings
LATEST_DISTANCE = None
LATEST_GPS = {"lat": None, "lon": None}

@app.route("/ultrasonic", methods=["POST"])
def ultrasonic_data():
    global LATEST_DISTANCE
    data = request.json
    distance = data.get("distance")

    if distance is not None:
        LATEST_DISTANCE = distance
        print(f"[INFO] Received ultrasonic distance: {distance} cm")
        return jsonify({"status": "received", "distance": distance})
    return jsonify({"error": "Distance not provided"}), 400

@app.route("/gps-data", methods=["POST"])
def gps_data():
    global LATEST_GPS
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")

    if lat and lon:
        LATEST_GPS = {"lat": lat, "lon": lon}
        print(f"[INFO] Received GPS: {lat}, {lon}")
        return jsonify({"status": "received", "lat": lat, "lon": lon})
    return jsonify({"error": "Latitude or longitude not provided"}), 400

@app.route("/latest-sensor-data", methods=["GET"])
def latest_sensor_data():
    return jsonify({
        "distance": LATEST_DISTANCE,
        "gps": LATEST_GPS
    })


def get_image_description(base64_image):
    API_KEY = "AIzaSyB4GgtY8Tkf6KeCx9CbkDykvSviN_bkmAg"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"

    prompt = '''
I am a blind individual, and I would like you to assist me in understanding images...
'''
    payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}},
                {"text": prompt}
            ]
        }]
    }

    try:
        res = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[ERROR] Gemini API error: {e}")
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
