# Outfit Mixer

Simple Flask web app to store your clothing items and generate mixed outfits.

Getting started

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

3. Open http://127.0.0.1:5000 in your browser. Add items with optional images and click "Generate Outfits" to see mixes.

Notes
- Uploaded images are saved to `static/uploads`.
- To reset database and uploads, use the "Clear All" button in the UI.
- Use the **Color Mode** selector to prefer matching or mixed-color outfits.
- Export generated outfits as JSON via the "Export JSON" button.
- Load example items with:

```bash
python sample_data.py
```

Camera capture

If your device has a camera, use the "Start Camera" button in the Add Item form to take a photo of a laid-out clothing item. The captured image will be uploaded and saved like a normal image file.

Docker

Build the container and run locally:

```bash
docker build -t outfit-mixer:latest .
docker run -p 5000:5000 --env FLASK_SECRET=replace-me outfit-mixer:latest
```

The app will be available at http://localhost:5000

Attribution

This app was created by Emily Tembo (age 13).
# outfit-mixer-2.O