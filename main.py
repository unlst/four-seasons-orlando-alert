from flask import Flask, jsonify
import threading
import requests
import time
import os

app = Flask(__name__)

# === CONFIG ===
CHECK_INTERVAL = 600  # 10 minutes
NTFY_TOPIC = "fs-orlando-jobs"
seen_jobs = set()

# Orlando Region ID for Workday (Florida -> Orlando subset)
WORKDAY_API = "https://fourseasons.wd3.myworkdayjobs.com/wday/cxs/fourseasons/Search/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# === JOB FETCHER ===
def get_jobs():
    # Orlando filter (Four Seasons Orlando)
    payload = {
        "appliedFacets": {"location": ["da6f2ff5d8a01013c48b0cf4c2005b02"]},  # Orlando’s Workday ID
        "searchText": ""
    }

    try:
        r = requests.post(WORKDAY_API, headers=HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"⚠️ Error fetching jobs: {e}")
        return []

    jobs = []
    for job in data.get("jobPostings", []):
        external_path = job.get("externalPath", "")
        job_id = external_path.split("/")[-1]
        title = job.get("title", "Unknown")
        location = job.get("locationsText", "Unknown")

        link = (
            f"https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/"
            f"{job_id}?location=da6f2ff5d8a01013c48b0cf4c2005b02"
        )

        jobs.append({
            "id": job.get("bulletFields", [external_path])[0],
            "title": title,
            "location": location,
            "link": link
        })

    print(f"✅ Found {len(jobs)} Orlando job(s)")
    return jobs

# === NOTIFICATION ===
def send_ntfy(job):
    message = f"📢 New Orlando job posted:\n{job['title']} in {job['location']}\n{job['link']}"
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), timeout=5)
        print(f"✅ Sent: {job['title']}")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

# === JOB LOOP ===
def job_alert_loop():
    global seen_jobs
    while True:
        try:
            jobs = get_jobs()
            for job in jobs:
                if job["id"] not in seen_jobs:
                    print(f"🔎 New job found: {job['title']} ({job['location']})")
                    send_ntfy(job)
                    seen_jobs.add(job["id"])
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)

# === STARTUP TEST ===
def send_startup_test():
    test_job = {
        "id": "TEST_ORLANDO",
        "title": "Test Orlando Job",
        "location": "Orlando",
        "link": "https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/TEST_ORLANDO"
    }
    send_ntfy(test_job)

# === FLASK ROUTES ===
@app.route("/")
def home():
    """Default route for Render health checks."""
    return "✅ Orlando Job Monitor is running", 200

@app.route("/ping")
def ping():
    """UptimeRobot endpoint."""
    return jsonify({"status": "alive", "service": "orlando-jobs"}), 200

# === STARTUP ===
if __name__ == "__main__":
    print("🚀 Orlando job monitor started...")
    send_startup_test()
    threading.Thread(target=job_alert_loop, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
