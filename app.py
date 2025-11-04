from flask import Flask, render_template, request
import json

app = Flask(__name__)

IMAGES_JSON = "images/images.json"

# Load image metadata
with open(IMAGES_JSON, "r") as f:
    images = json.load(f)

@app.route("/")
def index():
    # Pagination
    page = int(request.args.get("page", 1))
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    page_images = images[start:end]
    return render_template("index.html", images=page_images, page=page, total=len(images))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
