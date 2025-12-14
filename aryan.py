import cv2
import numpy as np
import re
import json
import sys
import os
import uuid
from difflib import SequenceMatcher
from ultralytics import YOLO
from paddleocr import PaddleOCR
import boto3
from botocore.exceptions import NoCredentialsError

UPLOAD_FOLDER = "/mnt/ebs100/uploads/"
RESULTS_FOLDER = "/mnt/ebs100/results/"
VIOLATION_IMG_FOLDER = "/mnt/ebs100/violations/"

os.environ['FLAGS_log_level'] = '3'

model = YOLO("yolov8n.pt")
ocr = PaddleOCR(lang="en")
s3 = boto3.client('s3')  # preload once

VALID_STATE_CODES = {"MH", "DL", "WB", "KA", "DD", "GJ", "TN", "PB", "UP", "TS"}
PLATE_REGEX = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'

def is_valid_plate(plate):
    return any(plate.startswith(code) for code in VALID_STATE_CODES)

def is_similar(plate1, plate2, threshold=0.85):
    return SequenceMatcher(None, plate1, plate2).ratio() >= threshold

def upload_to_s3(local_path, s3_bucket, s3_key):
    try:
        s3.upload_file(local_path, s3_bucket, s3_key)
        print(f"☁️ Uploaded to s3://{s3_bucket}/{s3_key}")
    except NoCredentialsError:
        print("⚠️ AWS credentials not found. Skipping S3 upload.")
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")

def detect_license_plates(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    detected_vehicles = []

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = 4

    if not cap.isOpened():
        print(f"❌ Error: Could not open video file {video_path}")
        return detected_vehicles

    os.makedirs(VIOLATION_IMG_FOLDER, exist_ok=True)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            results = model.predict(frame)

            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = map(int, box)
                    conf = confs[i]

                    if conf < 0.1 or (x2 - x1) < 70 or (y2 - y1) < 20:
                        continue

                    plate_region = frame[y1:y2, x1:x2]
                    ocr_results = ocr.ocr(plate_region, det=True, cls=True)
                    if not ocr_results:
                        ocr_results = ocr.ocr(plate_region, det=False, cls=True)


                    extracted_texts = [
                        r[1][0] for res in ocr_results if isinstance(res, list)
                        for r in res if isinstance(r, list) and len(r) > 1
                    ]
                    text = "".join(extracted_texts).replace(" ", "").upper()

                    if re.match(PLATE_REGEX, text) and is_valid_plate(text):
                        if not any(is_similar(text, existing) for existing in detected_vehicles):
                            detected_vehicles.append(text)

                            img_filename = f"{text}_{uuid.uuid4().hex[:6]}.jpg"
                            img_path = os.path.join(VIOLATION_IMG_FOLDER, img_filename)
                            cv2.imwrite(img_path, plate_region)

                            video_name = os.path.splitext(os.path.basename(video_path))[0]
                            s3_key = f"violations/{video_name}/{img_filename}"
                            upload_to_s3(img_path, "aryanpaode-project", s3_key)

        frame_count += 1

    cap.release()
    return detected_vehicles

def save_results_locally(result, video_name):
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    result_filename = os.path.join(RESULTS_FOLDER, f"{video_name}.json")

    try:
        with open(result_filename, "w") as f:
            json.dump(result, f, indent=4)
        print(f"✅ Results saved locally at: {result_filename}")
    except Exception as e:
        print(f"❌ Error saving results: {e}")
    return result_filename

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 aryan.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    print(f"🔍 Processing video: {video_name} ...")
    detected_plates = detect_license_plates(video_path)

    if detected_plates:
        print(f"📄 Detected Plates: {detected_plates}")
    else:
        print("⚠️ No plates detected.")

    result_file = save_results_locally(detected_plates, video_name)
    print(f"📂 Result stored at: {result_file}")

    try:
        upload_to_s3(
            local_path=result_file,
            s3_bucket="aryanpaode-project",
            s3_key=f"results/{os.path.basename(result_file)}"
        )
    except Exception as e:
        print(f"⚠️ Skipping S3 upload due to error: {e}")
