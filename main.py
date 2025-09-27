import requests
from flask import Flask, jsonify

app = Flask(__name__)

NTFY_TOPIC = "fs-orlando-jobs"
seen_jobs = set()

# Workday API endpoint
WORKDAY_API = "https://fourseasons.wd3.myworkdayjobs.com/wday/cxs/fourseasons/Search/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

# Payload for Florida jobs (we’ll filter Orlando after)
PAYLOAD = {
    "appliedFacets": {
        "locationRegionStateProvince": ["9c1a239b35bd4598856e5393b249b8a1"]
    },
    "limit": 20,
    "offset": 0,
    "searchText": ""
}

def get_jobs():
    """Fetch Florida jobs, filter for Orlando only."""
    try:
        r = requests.post(WORKDAY_API, headers=HEADERS, json=PAYLOAD, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"⚠️ Error fetching jobs: {e}")
        return []

    jobs = []
    for job in data.get("jobPostings", []):
        job_id = job.get("externalPath")
        job_title = job.get("title")
        job_location = job.get("locationsText", "Unknown")

        # ✅ Only include Orlando jobs
        if "Orlando" not in job_location:
            continue

        job_link = f"https://fourseasons.wd3.myworkdayjobs.com/en-US/fourseasons{job_id}"

        jobs.append({
            "id": job_id,
            "title": job_title,
            "location": job_location,
            "link": job_link
        })
    return jobs

def send_ntfy(message: str):
    """Send notification to NTFY."""
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), timeout=5)
        print(f"📢 Notification sent: {message}")
    except Exception as e:
        print(f"⚠️ Failed to send notification: {e}")

@app.route("/")
def home():
    """Root endpoint for UptimeRobot health checks."""
    return "✅ Orlando Job Alert Service is running"

@app.route("/check")
def check():
    """Endpoint to check for new Orlando jobs."""
    global seen_jobs
    jobs = get_jobs()
    new_jobs = []

    for job in jobs:
        if job["id"] not in seen_jobs:
            message = f"📌 New Orlando job posted:\n{job['title']} ({job['location']})\n{job['link']}"
            send_ntfy(message)
            seen_jobs.add(job["id"])
            new_jobs.append(job)

    # ✅ Properly closed dictionary
    return jsonify({
        "status": "ok",
        "new_jobs_found": len(new_jobs),
        "total_jobs": len(jobs)
    })

if __name__ == "__main__":
    # Send test notification on startup
    send_ntfy("🚀 Orlando Job Alert Service started and running on Render!")
    app.run(host="0.0.0.0", port=10000)
