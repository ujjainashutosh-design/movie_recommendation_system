import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob


class MovieRecommender:
    def __init__(self, csv_path="data/movies.csv"):
        self.df = pd.read_csv(csv_path)
        self.df["combined"] = self.df["genres"] + " " + self.df["overview"]

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["combined"])
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)

    def get_all_movies(self):
        return self.df.to_dict(orient="records")

    def get_movie(self, movie_id):
        row = self.df[self.df["id"] == movie_id]
        if row.empty:
            return None
        return row.to_dict(orient="records")[0]

    def search(self, query):
        query = query.lower()
        mask = (
            self.df["title"].str.lower().str.contains(query)
            | self.df["genres"].str.lower().str.contains(query)
        )
        return self.df[mask].to_dict(orient="records")

    def get_similar_movies(self, movie_id, top_n=5):
        idx_list = self.df.index[self.df["id"] == movie_id].tolist()
        if not idx_list:
            return []
        idx = idx_list[0]

        scores = list(enumerate(self.similarity_matrix[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        scores = [s for s in scores if s[0] != idx][:top_n]

        similar_movies = []
        for i, score in scores:
            movie = self.df.iloc[i].to_dict()
            movie["similarity"] = round(float(score), 2)
            similar_movies.append(movie)
        return similar_movies

    def get_recommendations_for_user(self, liked_movie_ids, top_n=6):
        if not liked_movie_ids:
            return self.df.sort_values("rating", ascending=False).head(top_n).to_dict(orient="records")

        indices = self.df.index[self.df["id"].isin(liked_movie_ids)].tolist()
        if not indices:
            return []

        avg_scores = self.similarity_matrix[indices].mean(axis=0)
        scored = list(enumerate(avg_scores))
        scored = sorted(scored, key=lambda x: x[1], reverse=True)
        scored = [s for s in scored if self.df.iloc[s[0]]["id"] not in liked_movie_ids][:top_n]

        recs = []
        for i, score in scored:
            movie = self.df.iloc[i].to_dict()
            movie["match_score"] = round(float(score) * 100, 1)
            recs.append(movie)
        return recs

    def analyze_review_sentiment(self, review_text):
        polarity = TextBlob(review_text).sentiment.polarity
        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"
        return {"polarity": round(polarity, 2), "label": label}