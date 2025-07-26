from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>Minimal Flask Test</h1><p>If you can see this, Flask is working!</p>'

if __name__ == '__main__':
    print("Starting minimal Flask app...")
    try:
        app.run(host='127.0.0.1', port=8888, debug=False)
    except Exception as e:
        print(f"Error starting Flask: {e}")