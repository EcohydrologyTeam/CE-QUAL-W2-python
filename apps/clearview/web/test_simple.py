#!/usr/bin/env python3
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Simple Flask Test Works!</h1>'

if __name__ == '__main__':
    print("Starting simple test on port 9996...")
    app.run(host='127.0.0.1', port=9996, debug=True)