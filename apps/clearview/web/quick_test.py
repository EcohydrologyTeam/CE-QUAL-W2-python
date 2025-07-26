from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'Flask is working on port 5000!'

app.run(debug=True)