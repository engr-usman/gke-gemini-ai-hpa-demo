# CampusBuzz AI on GKE with Gemini API

A simple AI-powered demo application that generates event summaries using **Gemini API**, runs on **Google Kubernetes Engine (GKE)**, and demonstrates **Horizontal Pod Autoscaling (HPA)** with a custom CPU load endpoint.

This project was built as part of a live university session on:

**Scaling Apps with GKE and Google AI Studio**

---

## Project Overview

This repository includes:

- **Frontend**: Simple HTML, CSS, and JavaScript UI served with Nginx
- **Backend**: Flask API with Gemini API integration
- **Container Registry**: Google Artifact Registry
- **Kubernetes Platform**: GKE Standard Zonal Cluster
- **Autoscaling**: Horizontal Pod Autoscaler (HPA)
- **Load Testing**: CPU burn endpoint for scaling demo

---

## Architecture

```text
User -> Frontend -> Backend -> Gemini API -> Response
```

### Flow
1. User opens the frontend application
2. Frontend sends a request to the backend `/generate` endpoint
3. Backend sends the prompt to Gemini API
4. Gemini API returns AI-generated content
5. Backend sends the response back to the frontend
6. HPA scales backend pods when CPU load increases

---

## Features

- AI-generated event summaries
- Frontend and backend deployed on GKE
- Backend exposed using LoadBalancer
- Frontend exposed using LoadBalancer
- HPA configured for automatic pod scaling
- `/cpu-burn` endpoint to simulate CPU load
- CORS enabled for frontend-backend communication
- Simple and clean demo UI for workshops and training sessions

---

## Project Structure

```text
.
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── deployment.yaml
│   └── service.yaml
├── frontend/
│   ├── index.html
│   ├── Dockerfile
│   ├── frontend-deployment.yaml
│   └── frontend-service.yaml
└── README.md
```

---

## Prerequisites

Before you begin, make sure you have:

- A Google Cloud project
- Billing enabled
- Google AI Studio / Gemini API access
- `gcloud` CLI installed
- `kubectl` installed
- Docker installed
- Docker Buildx available
- A supported GKE region and zone

### Recommended setup used in this project

- **Project ID**: `gke-gemini-demo`
- **Region**: `us-west1`
- **Zone**: `us-west1-c`
- **Cluster Name**: `gke-ai-demo-cluster`
- **Namespace**: `campus-demo`
- **Artifact Registry Repo**: `gke-ai-demo-repo`

---

## 1. Set Environment Variables

```bash
export PROJECT_ID="gke-gemini-demo"
export REGION="us-west1"
export ZONE="us-west1-c"
export CLUSTER_NAME="gke-ai-demo-cluster"
export NAMESPACE="campus-demo"
export REPO_NAME="gke-ai-demo-repo"
```

Configure your gcloud project:

```bash
gcloud config set project $PROJECT_ID
gcloud config set compute/zone $ZONE
gcloud config set compute/region $REGION
```

Verify:

```bash
gcloud config list
```

---

## 2. Enable Required APIs

```bash
gcloud services enable container.googleapis.com   artifactregistry.googleapis.com   cloudbuild.googleapis.com   compute.googleapis.com   monitoring.googleapis.com   logging.googleapis.com
```

---

## 3. Create GKE Cluster

This project uses a **Standard Zonal GKE Cluster**.

```bash
gcloud container clusters create $CLUSTER_NAME   --zone $ZONE   --num-nodes=1   --machine-type=e2-small   --disk-type=pd-standard   --disk-size=30   --project $PROJECT_ID
```

Connect `kubectl` to the cluster:

```bash
gcloud container clusters get-credentials $CLUSTER_NAME   --zone $ZONE   --project $PROJECT_ID
```

Verify cluster:

```bash
kubectl get nodes
kubectl get ns
```

Create namespace:

```bash
kubectl create namespace $NAMESPACE
```

---

## 4. Create Artifact Registry Repository

```bash
gcloud artifacts repositories create $REPO_NAME   --repository-format=docker   --location=$REGION   --description="Docker repo for GKE + Gemini demo"
```

Configure Docker authentication:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 5. Backend Setup

### 5.1 Create Backend Folder

```bash
mkdir -p backend
cd backend
```

### 5.2 Backend `requirements.txt`

```txt
flask
requests
flask-cors
```

### 5.3 Backend `app.py`

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@app.route("/")
def home():
    return "CampusBuzz AI backend is running on GKE 🚀"

@app.route("/env")
def env_check():
    return jsonify({
        "has_gemini_api_key": bool(GEMINI_API_KEY),
        "key_prefix": GEMINI_API_KEY[:10] if GEMINI_API_KEY else None
    })

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json or {}
    prompt = data.get("prompt", "")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, json=payload, timeout=60)

    if response.status_code != 200:
        return jsonify({
            "upstream_status": response.status_code,
            "upstream_body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }), 500

    result = response.json()

    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"response": text})
    except Exception:
        return jsonify({
            "message": "Gemini returned an unexpected payload",
            "raw_response": result
        }), 500

@app.route("/cpu-burn")
def cpu_burn():
    seconds = int(request.args.get("seconds", 20))
    end = time.time() + seconds
    x = 0

    while time.time() < end:
        for i in range(10000):
            x += i * i

    return jsonify({
        "message": f"CPU burn completed for {seconds} seconds",
        "dummy_result": x
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

### 5.4 Backend `Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]
```

### 5.5 Build and Push Backend Image

Set the backend image variable:

```bash
export IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/gke-ai-app:latest"
```

Build and push the image:

```bash
docker buildx build   --platform linux/amd64   -t $IMAGE_NAME   --push   .
```

> **Note:** `linux/amd64` is used because the image may be built from a Mac environment, while GKE nodes commonly run on amd64 architecture.

---

## 6. Create Gemini API Key

1. Open **Google AI Studio**
2. Create a Gemini API key
3. Make sure Gemini billing is enabled and funded
4. Keep the key ready for Kubernetes deployment

For local testing, you can export the key:

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

---

## 7. Deploy Backend on Kubernetes

### 7.1 Backend `deployment.yaml`

Replace `YOUR_GEMINI_API_KEY` with your actual Gemini API key.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-app
  namespace: campus-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-app
  template:
    metadata:
      labels:
        app: ai-app
    spec:
      containers:
      - name: ai-app
        image: us-west1-docker.pkg.dev/gke-gemini-demo/gke-ai-demo-repo/gke-ai-app:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
        env:
        - name: GEMINI_API_KEY
          value: "YOUR_GEMINI_API_KEY"
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

Apply the deployment:

```bash
kubectl apply -f deployment.yaml
kubectl rollout restart deployment ai-app -n campus-demo
kubectl get pods -n campus-demo -w
```

### 7.2 Backend `service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-service
  namespace: campus-demo
spec:
  type: LoadBalancer
  selector:
    app: ai-app
  ports:
    - port: 80
      targetPort: 8080
```

Apply the service:

```bash
kubectl apply -f service.yaml
kubectl get svc -n campus-demo
```

---

## 8. Test Backend

Replace the backend IP below with your actual backend LoadBalancer IP.

### Test AI generation

```bash
curl -X POST http://34.145.0.144/generate   -H "Content-Type: application/json"   -d '{"prompt":"Explain Kubernetes in simple words"}'
```

### Test CPU burn endpoint

```bash
curl "http://34.145.0.144/cpu-burn?seconds=5"
```

---

## 9. Configure Horizontal Pod Autoscaler

Create HPA:

```bash
kubectl autoscale deployment ai-app   -n campus-demo   --cpu-percent=50   --min=1   --max=5
```

Verify HPA and metrics:

```bash
kubectl get hpa -n campus-demo
kubectl describe hpa ai-app -n campus-demo
kubectl top pods -n campus-demo
kubectl top nodes
```

---

## 10. Scale Nodes Manually (if Needed)

If backend pods remain in `Pending` due to CPU shortage, increase node count.

Check node pools:

```bash
gcloud container node-pools list   --cluster gke-ai-demo-cluster   --zone us-west1-c   --project gke-gemini-demo
```

Resize the cluster to 2 nodes:

```bash
gcloud container clusters resize gke-ai-demo-cluster   --node-pool default-pool   --num-nodes 2   --zone us-west1-c   --project gke-gemini-demo
```

Verify:

```bash
kubectl get nodes
kubectl get pods -n campus-demo
```

---

## 11. Frontend Setup

### 11.1 Create Frontend Folder

```bash
cd ..
mkdir -p frontend
cd frontend
```

### 11.2 Frontend `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CampusBuzz AI</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: Arial, Helvetica, sans-serif;
    }

    body {
      background: linear-gradient(135deg, #0f172a, #1e293b);
      color: #fff;
      min-height: 100vh;
      padding: 40px 20px;
    }

    .container {
      max-width: 1100px;
      margin: 0 auto;
    }

    .hero {
      text-align: center;
      margin-bottom: 30px;
    }

    .hero h1 {
      font-size: 2.4rem;
      margin-bottom: 10px;
      color: #38bdf8;
    }

    .hero p {
      color: #cbd5e1;
      font-size: 1.05rem;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-top: 30px;
    }

    .card {
      background: rgba(15, 23, 42, 0.82);
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
      backdrop-filter: blur(8px);
    }

    .card h2 {
      margin-bottom: 18px;
      font-size: 1.3rem;
      color: #f8fafc;
    }

    label {
      display: block;
      margin-bottom: 8px;
      margin-top: 14px;
      color: #cbd5e1;
      font-size: 0.95rem;
    }

    input, textarea {
      width: 100%;
      padding: 14px;
      border-radius: 12px;
      border: 1px solid #334155;
      background: #0f172a;
      color: #fff;
      outline: none;
      font-size: 0.95rem;
    }

    textarea {
      min-height: 180px;
      resize: vertical;
    }

    input:focus, textarea:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.18);
    }

    .btn-row {
      display: flex;
      gap: 12px;
      margin-top: 20px;
      flex-wrap: wrap;
    }

    button {
      border: none;
      padding: 13px 18px;
      border-radius: 12px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: 0.2s ease;
    }

    .primary-btn {
      background: #38bdf8;
      color: #0f172a;
    }

    .primary-btn:hover {
      background: #0ea5e9;
    }

    .secondary-btn {
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid #334155;
    }

    .secondary-btn:hover {
      background: #334155;
    }

    .output-box {
      background: #020617;
      border: 1px solid #1e293b;
      border-radius: 14px;
      padding: 18px;
      min-height: 280px;
      white-space: pre-wrap;
      line-height: 1.6;
      color: #e2e8f0;
      overflow-wrap: anywhere;
    }

    .status {
      margin-top: 16px;
      padding: 12px 14px;
      border-radius: 12px;
      font-size: 0.92rem;
      display: none;
    }

    .status.success {
      display: block;
      background: rgba(34, 197, 94, 0.12);
      border: 1px solid rgba(34, 197, 94, 0.25);
      color: #86efac;
    }

    .status.error {
      display: block;
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.25);
      color: #fca5a5;
    }

    .footer-note {
      margin-top: 24px;
      text-align: center;
      color: #94a3b8;
      font-size: 0.92rem;
    }

    .badge {
      display: inline-block;
      margin-top: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(56, 189, 248, 0.12);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.25);
      font-size: 0.85rem;
    }

    @media (max-width: 900px) {
      .grid {
        grid-template-columns: 1fr;
      }

      .hero h1 {
        font-size: 2rem;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="hero">
      <h1>CampusBuzz AI</h1>
      <p>Generate event summaries using Gemini API on GKE and showcase scaling with Kubernetes HPA.</p>
      <div class="badge">GKE + Gemini API + HPA Demo</div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>Event Input</h2>

        <label for="title">Event Title</label>
        <input id="title" type="text" placeholder="e.g. Scaling Apps with GKE and Google AI Studio" />

        <label for="details">Event Details</label>
        <textarea id="details" placeholder="Write event details here..."></textarea>

        <div class="btn-row">
          <button class="primary-btn" onclick="generateContent()">Generate with AI</button>
          <button class="secondary-btn" onclick="fillSample()">Use Sample</button>
          <button class="secondary-btn" onclick="clearFields()">Clear</button>
        </div>

        <div id="statusBox" class="status"></div>
      </div>

      <div class="card">
        <h2>AI Generated Response</h2>
        <div id="output" class="output-box">Your AI-generated content will appear here...</div>
      </div>
    </div>

    <div class="footer-note">
      Demo flow: Enter event details -> Generate AI content -> Show HPA scaling separately in terminal
    </div>
  </div>

  <script>
    const BACKEND_URL = "http://34.145.0.144/generate";

    function setStatus(message, type) {
      const statusBox = document.getElementById("statusBox");
      statusBox.className = `status ${type}`;
      statusBox.innerText = message;
    }

    function clearFields() {
      document.getElementById("title").value = "";
      document.getElementById("details").value = "";
      document.getElementById("output").innerText = "Your AI-generated content will appear here...";
      const statusBox = document.getElementById("statusBox");
      statusBox.style.display = "none";
    }

    function fillSample() {
      document.getElementById("title").value = "Scaling Apps with GKE and Google AI Studio";
      document.getElementById("details").value =
        "An onsite university session for students on Kubernetes, Google Kubernetes Engine, autoscaling, and AI-powered application development using Gemini API. The session includes a live demo of container deployment, HPA testing, and AI-generated event content.";
      document.getElementById("output").innerText = "Sample content added. Click 'Generate with AI'.";
      setStatus("Sample data loaded successfully.", "success");
    }

    async function generateContent() {
      const title = document.getElementById("title").value.trim();
      const details = document.getElementById("details").value.trim();
      const output = document.getElementById("output");

      if (!title || !details) {
        setStatus("Please enter both event title and event details.", "error");
        return;
      }

      output.innerText = "Generating content, please wait...";
      setStatus("Sending request to backend...", "success");

      const prompt = `
Generate a short, attractive university event summary.

Event Title: ${title}
Event Details: ${details}

Requirements:
- Keep it simple and student-friendly
- Write a catchy summary
- Mention why students should attend
- Keep it concise but useful
`;

      try {
        const response = await fetch(BACKEND_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ prompt })
        });

        const data = await response.json();

        if (data.response) {
          output.innerText = data.response;
          setStatus("AI content generated successfully.", "success");
        } else {
          output.innerText = JSON.stringify(data, null, 2);
          setStatus("Backend responded, but AI output was not in expected format.", "error");
        }
      } catch (error) {
        output.innerText = "Error calling backend service.";
        setStatus("Failed to connect to backend service.", "error");
      }
    }
  </script>
</body>
</html>
```

### 11.3 Frontend `Dockerfile`

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
```

### 11.4 Build and Push Frontend Image

Set the frontend image variable:

```bash
export FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/campusbuzz-frontend:latest"
```

Build and push:

```bash
docker buildx build   --platform linux/amd64   -t $FRONTEND_IMAGE   --push   .
```

### 11.5 Frontend `frontend-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: campusbuzz-frontend
  namespace: campus-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: campusbuzz-frontend
  template:
    metadata:
      labels:
        app: campusbuzz-frontend
    spec:
      containers:
      - name: campusbuzz-frontend
        image: us-west1-docker.pkg.dev/gke-gemini-demo/gke-ai-demo-repo/campusbuzz-frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
```

Apply frontend deployment:

```bash
kubectl apply -f frontend-deployment.yaml
```

### 11.6 Frontend `frontend-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: campusbuzz-frontend-service
  namespace: campus-demo
spec:
  type: LoadBalancer
  selector:
    app: campusbuzz-frontend
  ports:
    - port: 80
      targetPort: 80
```

Apply frontend service:

```bash
kubectl apply -f frontend-service.yaml
kubectl get pods -n campus-demo
kubectl get svc -n campus-demo
```

---

## 12. Demo Commands

### Check health before demo

```bash
kubectl get nodes
kubectl get pods -n campus-demo
kubectl get svc -n campus-demo
kubectl get hpa -n campus-demo
kubectl top nodes
kubectl top pods -n campus-demo
```

### Add second node if needed

```bash
gcloud container node-pools list   --cluster gke-ai-demo-cluster   --zone us-west1-c   --project gke-gemini-demo
```

```bash
gcloud container clusters resize gke-ai-demo-cluster   --node-pool default-pool   --num-nodes 2   --zone us-west1-c   --project gke-gemini-demo
```

### Watch HPA and pods during demo

Terminal 1:

```bash
kubectl get hpa -n campus-demo -w
```

Terminal 2:

```bash
kubectl get pods -n campus-demo -w
```

Terminal 3 (optional):

```bash
kubectl top pods -n campus-demo
```

### Generate load to trigger scaling

```bash
for i in {1..20}; do
  curl "http://34.145.0.144/cpu-burn?seconds=20" &
done
wait
```

### Heavier load (optional)

```bash
for i in {1..30}; do
  curl "http://34.145.0.144/cpu-burn?seconds=25" &
done
wait
```

---

## 13. Common Issues Faced

During this project, the following issues were encountered and resolved:

- GKE quota issues
- SSD quota exceeded
- Node CPU shortage
- Pending pods due to insufficient resources
- Image architecture mismatch on Mac (`exec format error`)
- Gemini API disabled
- Gemini billing and credit issues
- CORS issue between frontend and backend

---

## 14. Troubleshooting Tips

### If pods are pending

```bash
kubectl describe pod <POD_NAME> -n campus-demo
```

### If HPA shows `<unknown>`

```bash
kubectl describe hpa ai-app -n campus-demo
kubectl top pods -n campus-demo
kubectl top nodes
```

### If frontend cannot call backend

- Check backend service IP
- Verify CORS is enabled in Flask
- Update `BACKEND_URL` in `index.html` if backend IP changes

### If Gemini API fails

- Verify Gemini API key
- Make sure Gemini billing is active
- Ensure the API is enabled
- Check the backend logs

```bash
kubectl logs deployment/ai-app -n campus-demo --tail=100
```

---

## 15. Suggested Improvements

Future improvements for this project:

- Move Gemini API key to Kubernetes Secret
- Use FastAPI instead of Flask
- Use React for frontend
- Add Ingress instead of separate LoadBalancer services
- Enable node autoscaling
- Add monitoring with Prometheus and Grafana
- Add authentication and logging

---

## 16. Cleanup Commands

Delete frontend:

```bash
kubectl delete -f frontend-service.yaml
kubectl delete -f frontend-deployment.yaml
```

Delete backend:

```bash
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
```

Delete HPA:

```bash
kubectl delete hpa ai-app -n campus-demo
```

Delete cluster:

```bash
gcloud container clusters delete $CLUSTER_NAME   --zone $ZONE   --project $PROJECT_ID
```

---

## 17. License

This project is for learning, workshops, demos, and educational use.

---

## 18. Author

**Usman Ahmad**  
AWS Cloud and DevOps Consultant  
Speaker | Trainer | Community Builder

If you found this project useful, feel free to connect and share your feedback.
