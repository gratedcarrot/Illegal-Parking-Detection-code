# Illegal Parking Detection System

This repository contains the final implementation of a cloud-enabled **Illegal Parking Detection System** developed and evaluated as part of an IEEE conference paper.

The system performs automated detection of illegally parked vehicles from video footage using a combination of:

- YOLOv8-based vehicle detection  
- OCR-based license plate recognition (PaddleOCR)  
- Temporal comparison across video frames  
- Cloud-based storage and processing on AWS EC2 and Amazon S3  

---

## System Overview

The system pipeline consists of the following stages:

1. Video upload through a web-based interface  
2. Periodic frame extraction from video streams  
3. Vehicle and license plate detection using deep learning  
4. OCR-based text extraction and validation  
5. Temporal comparison to identify persistent vehicle presence  
6. Generation of violation reports stored as JSON files  
7. Optional cloud archival of results to Amazon S3  

---

## Repository Contents

- `app.py` – Flask backend handling uploads, processing requests, comparison logic, and result retrieval  
- `aryan.py` – Core video processing pipeline using YOLOv8 and PaddleOCR  
- `frontend.html` – Web-based user interface for interacting with the system  
- `README.md` – Project documentation  

---

## Deployment Notes (Important)

This code reflects the **original AWS EC2 deployment environment** used for system evaluation in the accompanying IEEE conference paper.

Users intending to run the system in their own environment must update the following parameters according to their setup:

- Local storage paths (e.g., `/mnt/ebs100/uploads/`, `/mnt/ebs100/results/`, `/mnt/ebs100/violations/`)
- AWS EC2 instance type and attached EBS volume
- AWS S3 bucket name and credentials
- Network configuration (public IP address and exposed ports)

These paths and cloud resources are **hardcoded intentionally** to preserve fidelity with the evaluated system.

---

## AWS Credentials

AWS credentials are **not included** in this repository.

Users must configure credentials using one of the following methods:

- AWS CLI (`aws configure`)
- Environment variables
- IAM role attached to the EC2 instance

---

## Ethical Use and Data Privacy

All video data used in the associated research were collected with prior consent in controlled environments.

This system is provided **strictly for research and educational purposes** and is not intended for mass surveillance or unauthorized monitoring.

---

## Reproducibility

The source code in this repository corresponds exactly to the system version evaluated in the IEEE conference paper.

Paths, credentials, and infrastructure parameters may be adapted by users for their own deployments while preserving the core methodology.

---

## License

This project is released for **academic and research use only**.  
Commercial deployment or large-scale surveillance use requires independent ethical review and regulatory approval.
