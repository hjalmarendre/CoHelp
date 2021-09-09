import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

if __name__ == '__main__':
    app.run(debug=True)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///covid.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show messages from other users!"""
    if request.method == "GET":
        pend_jobs = db.execute("SELECT * FROM job WHERE helpid=:helpid AND accept = 0 AND finished = 0", helpid = session["user_id"])
        ass_jobs = db.execute("SELECT * FROM job WHERE helpid=:helpid AND accept = 1 AND finished = 0", helpid = session["user_id"])
        messages = db.execute("SELECT * FROM message WHERE to_id = :my_id", my_id=session["user_id"])
        print(messages)
        e = 0
        if not ass_jobs:
            return render_template("start.html", messages=messages, ass_jobs=ass_jobs, pend_jobs=pend_jobs)
        else:
                for name in ass_jobs:
                    name_help = db.execute("SELECT username from users WHERE id = :help_id", help_id = name.get("helperid"))
                    print(name_help[0]["username"])
                    name["username"] = name_help[0]
                    e =  e + 1
                    if e == len(ass_jobs)-1:
                        break
        return render_template("start.html", messages=messages, ass_jobs=ass_jobs, pend_jobs=pend_jobs)
    else:
        if request.form.get("response") == "":
            db.execute("DELETE FROM message WHERE mess_id = :mess_id", mess_id = request.form.get("mess_id"))
            flash("Message deleted!")
            return redirect("/")
        else:
            name = db.execute("SELECT username FROM users WHERE id=:my_id", my_id=session["user_id"])[0].get("username")
            response = request.form.get("response")
            subject = request.form.get("subject")
            to_id = request.form.get("to_id")
            db.execute("INSERT INTO message (name, subject, message, from_id, to_id) VALUES (:n, :s, :r, :f, :t)", n = name, s = subject, r = response, f = session["user_id"], t = to_id)
            flash("Message sent!")
        return redirect("/")


@app.route("/help", methods=["GET", "POST"])
@login_required
def cohelp():
    """Put in something that needs to be done"""
    if request.method == "GET":
        return render_template("help.html")
    else:
        title = request.form.get("title")
        help_type = request.form.get("type")
        desc = request.form.get("description")
        db.execute("INSERT INTO job (helpid, title, type, description) VALUES (:helpid, :title, :help_type, :description)", helpid = session["user_id"], title=title, help_type=help_type, description=desc)
        flash("Job added")
        return render_template("help.html")

    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of jobs"""
    jobslist = db.execute("SELECT * FROM job LEFT JOIN users ON job.helpid = users.id WHERE job.accept = 1 AND job.finished=1 AND job.helperid = :my_id", my_id = session["user_id"])
    print(jobslist[0]['title'])
    return render_template("history.html", jobslist = jobslist)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/find", methods=["GET", "POST"])
@login_required
def find():
    if request.method == "GET":
        comp_id = db.execute("SELECT * FROM users WHERE id = :my_id", my_id = session["user_id"])
        xcor_me = comp_id[0].get("xcor")
        ycor_me = comp_id[0].get("ycor")
        id_help = db.execute("SELECT * FROM users")
        jobslist = []
        for helpid in id_help:
            if xcor_me <= helpid.get("xcor") + 0.02 and xcor_me >= helpid.get("xcor") - 0.02 and helpid.get("id") != comp_id[0].get("id"):
                if ycor_me <= helpid.get("ycor") + 0.02 and ycor_me >= helpid.get("ycor") - 0.02:
                    jobslist.append(db.execute("SELECT * FROM job WHERE helpid = :helpid AND accept = 0", helpid = helpid.get("id")))
        return render_template("find.html", jobslist = jobslist)
    else:
        jobid = request.form.get("jobid")
        db.execute("UPDATE job SET helperid=:helperid,accept=:accept WHERE jobid = :jobid", helperid = session["user_id"], accept=1, jobid=jobid)

        comp_id = db.execute("SELECT * FROM users WHERE id = :my_id", my_id = session["user_id"])
        xcor_me = float(comp_id[0].get("xcor"))
        ycor_me = float(comp_id[0].get("ycor"))
        id_help = db.execute("SELECT * FROM users WHERE id = (SELECT helpid FROM job WHERE accept = 0)")
        jobslist = []
        for helpid in id_help:
            if xcor_me <= float(helpid.get("xcor") + 0.02) and xcor_me >= float(helpid.get("xcor") - 0.02) and helpid.get("id") != session["user_id"]:
                if ycor_me <= float(helpid.get("ycor") + 0.02) and ycor_me >= float(helpid.get("ycor") - 0.02):
                    jobslist.append(db.execute("SELECT * FROM job WHERE helpid = :helpid AND accept = 0", helpid = helpid.get("id")))
        if len(jobslist) > 0:
            jobslist = jobslist[0]
        flash("Job taken!")
        return render_template("find.html", jobslist = jobslist)

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        name = request.form.get("username")
        if not name:
            return render_template("register.html", message="You must provide a name.")

        password = request.form.get("password")
        if not password:
            return render_template("register.html", message="You must provide a password.")

        confirmation = request.form.get("confirmation")
        if not password == confirmation:
            return render_template("register.html", message="Password does not match.")

        xcor = request.form.get("x")
        ycor = request.form.get("y")
        if not xcor:
            return render_template("register.html", message="No coordinates was given, please choose your location with the map")

        search = db.execute("SELECT * FROM users WHERE username = :username", username = name)
        if len(search) == 0:
            pass_hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users (username, hash, xcor, ycor) VALUES (:name, :pass_hashed, :xcor, :ycor)", name=name, pass_hashed=pass_hashed, xcor=xcor, ycor=ycor)
        else:
            return render_template("register.html", message="Username already taken")
        flash("Account created!")
        return redirect("/")
    else:
        return render_template("register.html")

    return apology("Something went wrong")


@app.route("/current", methods=["GET", "POST"])
@login_required
def current():
    if request.method == "GET":
        xcor = db.execute("SELECT xcor FROM users WHERE id = :my_id", my_id = session["user_id"])
        ycor = db.execute("SELECT ycor FROM users WHERE id = :my_id", my_id = session["user_id"])
        jobslist = db.execute("SELECT * FROM job LEFT JOIN users ON job.helpid = users.id WHERE job.accept = 1 AND job.finished=0 AND job.helperid = :my_id", my_id = session["user_id"])
        return render_template("current.html", xcor = xcor, ycor=ycor, jobslist = jobslist)
    else:
        name = db.execute("SELECT username FROM users WHERE id=:my_id", my_id=session["user_id"])[0].get("username")
        response = request.form.get("response")
        subject = request.form.get("subject")
        helpid = request.form.get("to_id")
        if (response == ""):
            jobid = request.form.get("jobid")
            db.execute("UPDATE job SET finished=1 WHERE jobid = :jobid", jobid=jobid)
            xcor = db.execute("SELECT xcor FROM users WHERE id = :my_id", my_id = session["user_id"])
            ycor = db.execute("SELECT ycor FROM users WHERE id = :my_id", my_id = session["user_id"])
            jobslist = db.execute("SELECT * FROM job LEFT JOIN users ON job.helpid = users.id WHERE job.accept = 1 AND job.finished=0 AND job.helperid = :my_id", my_id = session["user_id"])
            return render_template("current.html", xcor = xcor, ycor=ycor, jobslist = jobslist)
        else:
            #A message was sent!
            db.execute("INSERT INTO message (name, subject, message, from_id, to_id) VALUES (:n, :s, :r, :f, :t)", n = name, s = subject, r = response, f = session["user_id"], t = helpid)
            flash("Message sent!")
            return redirect("/current")
    return apology("Something went wrong")

@app.route("/profile")
@login_required
def profile():
        jobs_done = len(db.execute("SELECT * FROM job LEFT JOIN users ON job.helpid = users.id WHERE job.accept = 1 AND job.finished=1 AND job.helperid = :my_id", my_id = session["user_id"]))
        user_info = db.execute("SELECT * from USERS WHERE id = :my_id", my_id = session["user_id"])[0]
        print(user_info)
        return render_template("profile.html", user_info = user_info, jobs_done = jobs_done)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
