from flask import Flask, render_template, url_for

app = Flask(__name__)
app.config.from_object(__name__)
