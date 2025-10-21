from flask import Flask, jsonify
import threading
import requests
import time
import os

app = Flask(__name__)

# === CONFIG ===
CHECK_INTERVAL = 600  # 10 minutes
FLORIDA_TOPIC = "fs-florida-jobs"
ORLANDO_TOPIC = "fs-orlando-jobs"

seen_florida_jobs = set()
seen_orlando_jobs = set()

WORKDAY_API = "https://fourseasons.wd3.myworkdayjobs.com/wday/cxs/fourseasons/Search/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# === JOB FETCHER ===
def fetch_jobs(search_text=""):
    payload = {
        "appliedFacets": {
            "locationHierarchy1": ["9c1a239b35bd4598856e5393b249b8a1"]  # Florida
        },
        "limit": 50,
        "offset": 0,
        "searchText": search_text
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
        external_path = job.get("externalPath", "")
        job_id = external_path.split("/")[-1]
        link = f"https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/{job_id}?locationRegionStateProvince=9c1a239b35bd4598856e5393b249b8a1"

        jobs.append({
            "id": job.get("bulletFields", [external_path])[0],
            "title": job.get("title", "Unknown"),
            "location": job.get("locationsText", "Unknown"),
            "link": link
        })
    return jobs

# === NTFY NOTIFICATION ===
def send_ntfy(job, topic):
    message = f"📢 New job posted:\n{job['title']} in {job['location']}\n{job['link']}"
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"), timeout=5)
        print(f"✅ Sent to {topic}: {job['title']}")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

# === JOB MONITOR LOOP ===
def job_loop(topic, seen_jobs, city_filter=None):
    while True:
        try:
            jobs = fetch_jobs()
            if city_filter:
                jobs = [j for j in jobs if city_filter in j["location"]]

            for job in jobs:
                if job["id"] not in seen_jobs:
                    send_ntfy(job, topic)
                    seen_jobs.add(job["id"])

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"⚠️ Unexpected error in {topic} loop: {e}")
            time.sleep(CHECK_INTERVAL)

# === START BACKGROUND THREADS ===
threading.Thread(target=job_loop, args=(FLORIDA_TOPIC, seen_florida_jobs, None), daemon=True).start()
threading.Thread(target=job_loop, args=(ORLANDO_TOPIC, seen_orlando_jobs, "Orlando"), daemon=True).start()

# === STARTUP TEST NOTIFICATIONS ===
def send_startup_tests():
    send_ntfy({"id": "TEST_FL", "title": "Test Florida Job", "location": "Florida", "link": "https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/TEST_FL"}, FLORIDA_TOPIC)
    send_ntfy({"id": "TEST_ORL", "title": "Test Orlando Job", "location": "Orlando", "link": "https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/TEST_ORL"}, ORLANDO_TOPIC)

send_startup_tests()

# === KEEP-ALIVE ENDPOINT ===
@app.route("/ping")
def ping():
    return jsonify({"status": "ok", "message": "Florida & Orlando job monitor running ✅"}), 200

# === RUN FLASK ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("🚀 Florida & Orlando job monitor started...")
    app.run(host="0.0.0.0", port=port)
