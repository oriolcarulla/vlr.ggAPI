from flask import Flask, jsonify
import json

app = Flask(__name__)

# Carga el archivo JSON
with open('matches_by_event.json', encoding="utf-8") as json_file:
    data = json.load(json_file)

@app.route('/api', methods=['GET'])
def get_data():
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)