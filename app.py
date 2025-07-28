from flask import Flask

app = Flask(__name__)

@app.route("/")
def Nomad_Co():
    return "<p>Hello,Everyone This is the Nomad Co. App</p>"