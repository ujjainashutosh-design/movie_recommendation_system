from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from recommend import MovieRecommender

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this"

recommender = MovieRecommender("data/movies.csv")

USERS = {}
RATINGS = {}
WATCHLIST = {}
REVIEWS = {}


def current_user():
    return session.get("username")

GENRE_COLORS = {
    "Action": "#d8473a, #7c1f1f",
    "Adventure": "#22a87b, #0c4730",
    "Sci-Fi": "#22d3ee, #1e3a8a",
    "Drama": "#7c5cf0, #2c1f5c",
    "Comedy": "#f0b429, #8a5a0c",
    "Romance": "#f4528e, #6b1d3a",
    "Crime": "#5f5e5a, #1a1a1a",
    "Thriller": "#9b2c2c, #2c0a0a",
    "Horror": "#1a1a2e, #4a0e0e",
    "Musical": "#d946ef, #581c87",
    "Music": "#d946ef, #581c87",
    "Animation": "#34d399, #0c4a3e",
    "Family": "#fbbf24, #78350f",
    "Fantasy": "#a78bfa, #3b0764",
    "Biography": "#60a5fa, #1e3a8a",
    "History": "#b45309, #451a03",
    "Sport": "#16a34a, #052e16",
    "Mystery": "#4338ca, #1e1b4b",
}


@app.template_filter("genre_color")
def genre_color(genres_str):
    first_genre = genres_str.split(" ")[0]
    return GENRE_COLORS.get(first_genre, "#7c5cf0, #1a1033")


@app.route("/industry/<industry>")
def filter_industry(industry):
    movies = [m for m in recommender.get_all_movies() if m["industry"] == industry]
    return render_template(
        "index.html",
        movies=movies,
        user=current_user(),
        page_title=f"{industry.lower()} movies",
        industry_filter=industry,
    )
@app.route("/")
def home():
    if not current_user():
        return redirect(url_for("login"))
    movies = recommender.get_all_movies()
    top_movies = sorted(movies, key=lambda m: m["rating"], reverse=True)[:8]
    return render_template("index.html", movies=top_movies, user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        if username:
            session["username"] = username
            USERS.setdefault(username, {"joined": True})
            RATINGS.setdefault(username, {})
            WATCHLIST.setdefault(username, [])
            return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = recommender.search(query) if query else []
    return render_template("index.html", movies=results, user=current_user(), search_query=query)


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = recommender.get_movie(movie_id)
    if not movie:
        return "Movie not found", 404
    similar = recommender.get_similar_movies(movie_id, top_n=4)
    user = current_user()
    user_rating = RATINGS.get(user, {}).get(movie_id) if user else None
    in_watchlist = movie_id in WATCHLIST.get(user, []) if user else False
    movie_reviews = REVIEWS.get(movie_id, [])
    return render_template(
        "movie.html",
        movie=movie,
        similar=similar,
        user=user,
        user_rating=user_rating,
        in_watchlist=in_watchlist,
        reviews=movie_reviews,
    )


@app.route("/rate/<int:movie_id>", methods=["POST"])
def rate_movie(movie_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    rating = int(request.form["rating"])
    RATINGS.setdefault(user, {})[movie_id] = rating
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/review/<int:movie_id>", methods=["POST"])
def add_review(movie_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    text = request.form["review_text"].strip()
    if text:
        sentiment = recommender.analyze_review_sentiment(text)
        REVIEWS.setdefault(movie_id, []).append(
            {"user": user, "text": text, "sentiment": sentiment}
        )
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/watchlist/add/<int:movie_id>", methods=["POST"])
def add_watchlist(movie_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if movie_id not in WATCHLIST.setdefault(user, []):
        WATCHLIST[user].append(movie_id)
    return redirect(request.referrer or url_for("home"))


@app.route("/watchlist/remove/<int:movie_id>", methods=["POST"])
def remove_watchlist(movie_id):
    user = current_user()
    if user and movie_id in WATCHLIST.get(user, []):
        WATCHLIST[user].remove(movie_id)
    return redirect(request.referrer or url_for("home"))


@app.route("/watchlist")
def view_watchlist():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    ids = WATCHLIST.get(user, [])
    movies = [recommender.get_movie(i) for i in ids]
    return render_template("index.html", movies=movies, user=user, page_title="my watchlist")


@app.route("/recommendations")
def recommendations():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    liked_ids = [mid for mid, r in RATINGS.get(user, {}).items() if r >= 4]
    recs = recommender.get_recommendations_for_user(liked_ids, top_n=6)
    return render_template("recommendations.html", movies=recs, user=user)


if __name__ == "__main__":
    app.run(debug=True, port=5000)