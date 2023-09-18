from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreatePostReplyForm
from sqlalchemy import update
from sqlalchemy.sql import column
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.exc import IntegrityError
import datetime as dt
import os

app = Flask(__name__)
login_manager = LoginManager()
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
db = SQLAlchemy()
db.init_app(app)
Bootstrap5(app)
login_manager.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(30), nullable=False)


class Post(UserMixin, db.Model):
    __tablename__ = "posts"
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    reply_count = db.Column(db.Integer, nullable=False)
    last_reply = db.Column(db.String(50), nullable=False)
    author_id = db.Column(db.String(30), db.ForeignKey('users.username'), nullable=False)

class Reply(UserMixin, db.Model):
    __tablename__ = "replies"
    reply_id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    author_id = db.Column(db.String(30), db.ForeignKey('users.username'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


@app.route("/", methods=["GET", "POST"])
def home_page():
    page_title = "Home Page"
    all_posts = db.session.query(Post).order_by(Post.last_reply.desc()).all()

    return render_template("index.html", page_title=page_title, current_user=current_user, all_posts=all_posts)


@app.route("/register", methods=["GET", "POST"])
def register_page():
    page_title = "Register"

    if request.method == "POST":
        username = request.form.get("usernameInput")
        password = request.form.get("passwordInput")
        hashed_password = generate_password_hash(password=password, method='pbkdf2', salt_length=8)
        new_user = User(
            username=username,
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            return redirect(url_for('home_page'))
        except IntegrityError:
            error = "Username already exists"
            return render_template("register.html", error=error, page_title=page_title, current_user=current_user)

    return render_template("register.html", page_title=page_title, current_user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        page_title = "Register"
        username = request.form.get("usernameInput")
        password = request.form.get("passwordInput")
        result = db.session.execute(db.select(User).where(User.username == username))
        user = result.scalar()

        if not user:
            error = "Username was not found"
            return render_template("register.html", error=error, page_title=page_title)
        elif not check_password_hash(user.password, password):
            error = "Password is incorrect"
            return render_template("register.html", error=error, page_title=page_title)
        else:
            login_user(user)
            return redirect(url_for("home_page"))

    return redirect(url_for("home_page"))


@app.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    page_title = "New Post"
    form = CreatePostForm()
    if request.method == "POST" and form.validate_on_submit():
        new_post = Post(
            title=form.title.data,
            body=form.body.data,
            author_id=current_user.username,
            reply_count = 0,
            date=dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            last_reply=dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        )

        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home_page"))

    return render_template("new_post.html", page_title=page_title, form=form)


@app.route("/show_post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    page_title = f"Post {post_id}"
    form = CreatePostReplyForm()
    post = db.get_or_404(Post, post_id)
    all_replies = db.session.execute(db.select(Reply).where(Reply.post_id == post_id)).scalars().all()

    if request.method == "POST":
        reply_content = form.body.data
        username = current_user.username
        date = dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        new_reply_count = post.reply_count + 1

        reply = Reply(
            body=reply_content,
            author_id=username,
            date=date,
            post_id=post_id
        )

        db.session.query(Post).filter(Post.post_id == post_id).update({'last_reply': date})
        db.session.query(Post).filter(Post.post_id == post_id).update({'reply_count': new_reply_count})
        db.session.add(reply)
        db.session.commit()

        return redirect(f"{post_id}")

    return render_template("show_post.html", page_title=page_title, post=post, replies=all_replies, form=form, current_user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
