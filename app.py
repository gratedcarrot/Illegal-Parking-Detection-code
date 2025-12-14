from flask import Flask, request, jsonify, render_template
import os
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from flask_cors import CORS



app = Flask(__name__)

CORS(app)  

UPLOAD_FOLDER = "/mnt/ebs100/uploads/"
RESULTS_FOLDER = "/mnt/ebs100/results/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

@app.route('/')
def index():
    return render_template('frontend.html')

@app.route('/list_videos', methods=['GET'])
def list_videos():
    try:
        videos = sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.mp4', '.mov'))])
        return jsonify({'videos': videos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    return jsonify({'message': 'File uploaded successfully', 'filename': filename})

@app.route('/process', methods=['POST'])
def process_video():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'})

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    result_path = os.path.join(app.config['RESULTS_FOLDER'], filename.replace('.mov', '.json'))

    if not os.path.exists(video_path):
        return jsonify({'error': 'File not found'})

    try:
        subprocess.run(["python3", "/mnt/ebs100/flask_app/aryan.py", video_path], check=True)

    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Processing failed', 'details': str(e)})

    return jsonify({'message': 'Processing completed', 'result_file': result_path})

import json

@app.route('/compare_videos', methods=['POST'])
def compare_videos():
    data = request.json
    video1 = data.get('video1')
    video2 = data.get('video2')

    if not video1 or not video2:
        return jsonify({'error': 'Both filenames are required'}), 400

    file1 = os.path.join(RESULTS_FOLDER, f"{video1}.json")
    file2 = os.path.join(RESULTS_FOLDER, f"{video2}.json")

    if not os.path.exists(file1) or not os.path.exists(file2):
        return jsonify({'error': 'One or both result files not found'}), 404

    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        try:
            plates1 = json.load(f1)
            plates2 = json.load(f2)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format'}), 500

    common_plates = list(set(plates1) & set(plates2))

    # Save summary
    summary = {
        "video1": video1,
        "video2": video2,
        "violating_plates": common_plates,
        "violation_type": "Common vehicle detection (likely violation)"
    }

    summary_filename = f"{video1}_{video2}_violation.json"
    summary_path = os.path.join(RESULTS_FOLDER, summary_filename)

    with open(summary_path, 'w') as sf:
        json.dump(summary, sf, indent=4)

    # Optional: Upload to S3
    try:
        from aryan import upload_to_s3
        upload_to_s3(summary_path, "aryanpaode-project", f"violations/{summary_filename}")
    except Exception as e:
        print(f"⚠️ Skipping S3 upload of violation summary: {e}")

    return jsonify({'common_plates': common_plates})



@app.route('/results', methods=['GET'])
def get_results():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename is required'})

   
    filename = os.path.splitext(filename)[0] + ".json"

    result_path = os.path.join(app.config['RESULTS_FOLDER'], filename)

    if not os.path.exists(result_path):
        return jsonify({'error': 'Result file not found'})

    with open(result_path, 'r') as f:
        results = json.load(f)

    return jsonify({'results': results})



if __name__ == '__main__':
    logging.basicConfig(
        handlers=[RotatingFileHandler("/mnt/ebs100/flask_app/flask.log", maxBytes=100000, backupCount=3)],
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    app.run(host='0.0.0.0', port=5000, debug=True)
