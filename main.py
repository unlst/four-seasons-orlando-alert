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

# Workday API for Four Seasons
WORKDAY_API = "https://fourseasons.wd3.myworkdayjobs.com/wday/cxs/fourseasons/Search/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


# === GET JOBS ===
def get_orlando_jobs():
    """Fetch and filter job listings for Orlando only."""
    payload = {
        "appliedFacets": {},
        "searchText": "Orlando"
    }

    try:
        r = requests.post(WORKDAY_API, headers=HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")
        return []

    jobs = []
    for job in data.get("jobPostings", []):
        title = job.get("title", "Unknown")
        location = job.get("locationsText", "Unknown")
        external_path = job.get("externalPath", "")
        job_id = external_path.split("/")[-1]
        link = f"https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/{job_id}"

        # Filter only Orlando postings
        if "Orlando" in location or "Orlando" in title:
            jobs.append({
                "id": job_id,
                "title": title,
                "location": location,
                "link": link
            })
    return jobs


# === SEND NOTIFICATION ===
def send_ntfy(job):
    message = f"📢 New Orlando job posted:\n{job['title']} in {job['location']}\n{job['link']}"
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), timeout=5)
        print(f"✅ Sent: {job['title']}")
    except Exception as e:
        print(f"⚠️ Notification failed: {e}")


# === BACKGROUND LOOP ===
def job_alert_loop():
    global seen_jobs
    print("🚀 Orlando job monitor started...")
    while True:
        try:
            jobs = get_orlando_jobs()
            for job in jobs:
                if job["id"] not in seen_jobs:
                    send_ntfy(job)
                    seen_jobs.add(job["id"])
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"⚠️ Loop error: {e}")
            time.sleep(CHECK_INTERVAL)


# === TEST NOTIFICATION ON STARTUP ===
def send_startup_test():
    test_job = {
        "id": "TEST_ORL",
        "title": "Test Orlando Job",
        "location": "Orlando, FL",
        "link": "https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/TEST_ORL"
    }
    send_ntfy(test_job)


# === FLASK ROUTES ===
@app.route("/ping")
def ping():
    """For uptime monitoring — instant 200 OK."""
    return jsonify({"status": "alive"}), 200


@app.route("/check")
def manual_check():
    """Manually trigger a job scan."""
    jobs = get_orlando_jobs()
    return jsonify({
        "found": len(jobs),
        "jobs": jobs[:5]  # return preview of first 5
    }), 200


# === START EVERYTHING ===
threading.Thread(target=job_alert_loop, daemon=True).start()
send_startup_test()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
