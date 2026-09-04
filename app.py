from flask import Flask, render_template, request, jsonify

from scraper import scrape_prices


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# SEARCH API
# =========================================================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    location = request.args.get(
        "location",
        "mumbai"
    ).strip()

    # -----------------------------------------------------
    # Empty query
    # -----------------------------------------------------

    if not query:

        return jsonify({
            "error":
                "Please enter a product name."
        }), 400

    print("\n")
    print("=" * 50)
    print(
        f"SEARCH REQUEST: {query} | LOCATION: {location}"
    )
    print("=" * 50)

    try:

        products = scrape_prices(
            query,
            location=location
        )

        return jsonify(
            products
        )

    except Exception as e:

        print(
            "PriceSense engine error:",
            e
        )

        return jsonify({
            "error":
                "Unable to collect price data.",
            "details":
                str(e)
        }), 500


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=8000
    )