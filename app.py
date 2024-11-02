import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///music.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # no username submission
        if not request.form.get("username"):
            error = "error: must provide username!"
            return render_template("apology.html", error=error)

        # no password submission
        elif not request.form.get("password"):
            error = "error: must provide password!"
            return render_template("apology.html", error=error)

        # query users for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            error = "error: invalid username and/or password!"
            return render_template("apology.html", error=error)

        # keep track of which user is on
        session["user_id"] = rows[0]["id"]

        # redirect user to complete survey
        return redirect("/survey")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":
        # no username submission
        if not request.form.get("username"):
            error = "error: must provide username!"
            return render_template("apology.html", error=error)
        # no password submission
        elif not request.form.get("password"):
            error = "error: must provide password!"
            return render_template("apology.html", error=error)
        # no confirmation submission
        elif not request.form.get("password"):
            error = "error: must confirm password!"
            return render_template("apology.html", error=error)
        # no password match
        elif request.form.get("password") != request.form.get("confirmation"):
            error = "error: passwords must match!"
            return render_template("apology.html", error=error)
        # query users for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # check username
        if len(rows) == 1:
            error = "error: username already taken!"
            return render_template("apology.html", error=error)
        # hash password
        hash = generate_password_hash(request.form.get("password"))
        # insert newly registered user into database
        user = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"), hash)
        session["user_id"] = user
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/survey", methods=["GET", "POST"])
@login_required
def survey():
    """Questionnaire for recommendations"""

    if request.method == "POST":
        # keep track of which user is on
        user_id = session["user_id"]

        # check empty fields
        if not request.form.get("danceability") or not request.form.get("energy") or not request.form.get("valence"):
            error = "error: must fill out all fields!"
            return render_template("apology.html", error=error)

        # gather input
        danceability = int(request.form.get("danceability"))
        energy = int(request.form.get("energy"))
        valence = int(request.form.get("valence"))
        explicit = request.form.get("explicitness")

        # establish range for SQL query based on input
        max_danceability = danceability / 10 + 0.1
        min_danceability = max_danceability - 0.2

        max_energy = energy / 10 + 0.1
        min_energy = max_energy - 0.2

        max_valence = valence / 10 + 0.1
        min_valence = max_valence - 0.2

        # query for explicit and non-explicit songs or only non-explicit songs
        if explicit == "Yes":
            recommendations = db.execute("SELECT * FROM music WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? ORDER BY RANDOM() LIMIT 5", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence)
        else:
            explicit = 0
            recommendations = db.execute("SELECT * FROM music WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? AND explicit = ? ORDER BY RANDOM() LIMIT 5", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence, explicit)

        if not recommendations:
            error = "Sorry :(, none of the songs from the database match your preferences. Please try again with different values!"
            return render_template("apology.html", error=error)

        for recommendation in recommendations:
            # insert songs into recommendations history
            db.execute("INSERT INTO recommended (user_id, name, artists, danceability, energy, valence, explicit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        user_id, recommendation["name"], recommendation["artists"], recommendation["danceability"], recommendation["energy"], recommendation["valence"], recommendation["explicit"])

            # insert user input into survey data database
            db.execute("INSERT INTO survey_data (user_id, danceability, energy, valence) VALUES (?, ?, ?, ?)",
                        user_id, danceability, energy, valence)

        return render_template("recommendation.html", recommendations=recommendations)

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("survey.html")

@app.route("/")
@login_required
def recommended():
    """Show all previous recommendations"""
    # keep track of current user
    user_id = session["user_id"]

    recommended = db.execute("SELECT DISTINCT name, artists FROM recommended WHERE user_id = ?", user_id)

    return render_template("recommended.html", recommended=recommended)

@app.route("/data")
@login_required
def data():
    """Show all previous recommendations"""
    # keep track of current user
    user_id = session["user_id"]

    # query database for averages
    personal_averages = db.execute("SELECT AVG(danceability), AVG(energy), AVG(valence) FROM survey_data WHERE user_id = ?", user_id)
    song_averages = db.execute("SELECT AVG(danceability), AVG(energy), AVG(valence) FROM recommended WHERE user_id = ?", user_id)

    return render_template("data.html", personal_averages=personal_averages, song_averages=song_averages)

@app.route("/playlists", methods=["GET", "POST"])
@login_required
def playlists():
    """Show curated playlists"""
    return render_template("playlists.html")

@app.route("/about", methods=["GET", "POST"])
@login_required
def about():
    """Display about us"""
    return render_template("about.html")

@app.route("/artist_survey", methods=["GET", "POST"])
@login_required
def artist_survey():
    """Questionnaire for a specific artist recommendation"""

    if request.method == "POST":
        user_id = session["user_id"]

        # check empty fields
        if not request.form.get("danceability") or not request.form.get("energy") or not request.form.get("valence"):
            error = "error: must fill out all fields!"
            return render_template("apology.html", error=error)

        # gather input
        person = request.form.get("person")
        danceability = int(request.form.get("danceability"))
        energy = int(request.form.get("energy"))
        valence = int(request.form.get("valence"))
        explicit = request.form.get("explicitness")

        # establish ranges depending on artist data
        max_danceability = danceability / 10 + 0.3
        max_energy = energy / 10 + 0.3
        max_valence = valence / 10 + 0.3

        if person == "Kevin":
            if max_danceability > 0.89:
                max_danceability = 0.89
            elif max_energy > 1:
                max_energy = 1
            elif max_valence > 1:
                max_valence = 1

            min_danceability = max_danceability - 0.4
            min_energy = max_energy - 0.4
            min_valence = max_valence - 0.4

            if min_danceability < 0.3:
                min_danceability = 0.3
            elif min_energy < 0.28:
                min_energy = 0.28
            elif min_valence < 0.07:
                min_valence = 0.07

            # query for explicit and non-explicit songs or only non-explicit songs
            if explicit == "Yes":
                recommendations = db.execute("SELECT * FROM selena_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence)
            else:
                explicitness = "FALSE"
                recommendations = db.execute("SELECT * FROM selena_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? AND explicit = ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence, explicitness)

        elif person == "Emi":
            if max_danceability > 0.8:
                max_danceability = 0.8
            if max_energy > 1:
                max_energy = 1
            if max_valence > 0.67:
                max_valence = 0.67

            min_danceability = max_danceability - 0.4
            min_energy = max_energy - 0.4
            min_valence = max_valence - 0.4

            if min_danceability < 0.14:
                min_danceability = 0.14
            elif min_energy < 0.07:
                min_energy = 0.07
            elif min_valence < 0.04:
                min_valence = 0.07

            # query for explicit and non-explicit songs or only non-explicit songs
            if explicit == "Yes":
                recommendations = db.execute("SELECT * FROM lana_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence)
            else:
                explicitness = "FALSE"
                recommendations = db.execute("SELECT * FROM lana_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? AND explicit = ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence, explicitness)

        else:
            if max_danceability > 0.9:
                max_danceability = 0.9
            if max_energy > 0.95:
                max_energy = 0.95
            if max_valence > 0.97:
                max_valence = 0.97

            min_danceability = max_danceability - 0.4
            min_energy = max_energy - 0.4
            min_valence = max_valence - 0.4

            if min_danceability < 0.17:
                min_danceability = 0.17
            elif min_energy < 0.06:
                min_energy = 0.06
            elif min_valence < 0.04:
                min_valence = 0.04

            # query for explicit and non-explicit songs or only non-explicit songs
            if explicit == "Yes":
                recommendations = db.execute("SELECT * FROM taylor_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence)
            else:
                explicitness = "FALSE"
                recommendations = db.execute("SELECT * FROM taylor_data WHERE danceability BETWEEN ? and ? AND energy BETWEEN ? and ? AND valence BETWEEN ? and ? AND explicit = ? ORDER BY RANDOM() LIMIT 1", min_danceability, max_danceability, min_energy, max_energy, min_valence, max_valence, explicitness)

        if not recommendations:
            error = "Sorry :(, none of the songs from the database match your preferences. Please try again with different values!"
            return render_template("apology.html", error=error)

        for recommendation in recommendations:
            # insert song into recommendations history
            db.execute("INSERT INTO recommended (user_id, name, artists, danceability, energy, valence, explicit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        user_id, recommendation["track_name"], recommendation["artist_name"], recommendation["danceability"], recommendation["energy"], recommendation["valence"], recommendation["explicit"])

            # insert user input into survey data database
            db.execute("INSERT INTO survey_data (user_id, danceability, energy, valence) VALUES (?, ?, ?, ?)",
                        user_id, danceability, energy, valence)

        return render_template("artist_recommendation.html",recommendations=recommendations)

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("artist_survey.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect("/")


