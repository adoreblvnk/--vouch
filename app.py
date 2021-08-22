import os
from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template("index.html")
