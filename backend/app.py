from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This allows cross-origin requests from React app

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({
        "message": "Hello from the Stouffville By-laws AI backend!"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


