from flask import Flask, request, redirect, render_template
import string
import random

app = Flask(__name__)

# Database sederhana untuk menyimpan URL
url_database = {}

def generate_short_url(length=6):
    """Menghasilkan URL pendek secara acak."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        original_url = request.form["url"]
        short_url = generate_short_url()

        # Simpan original_url dengan short_url
        url_database[short_url] = original_url

        return render_template("index.html", short_url=short_url)

    return render_template("index.html")

@app.route("/<short_url>")
def redirect_to_url(short_url):
    original_url = url_database.get(short_url)
    if original_url:
        return redirect(original_url)
    return "URL tidak ditemukan!", 404

if __name__ == "__main__":
    app.run(debug=True)
