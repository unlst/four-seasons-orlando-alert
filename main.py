import requests
import time

# CONFIG
CHECK_INTERVAL = 600  # 10 minutes
NTFY_TOPIC = "fs-orlando-jobs"
seen_jobs = set()

WORKDAY_API = "https://fourseasons.wd3.myworkdayjobs.com/wday/cxs/fourseasons/Search/jobs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_jobs():
    payload = {
        "appliedFacets": {
            "locationRegionStateProvince": ["9c1a239b35bd4598856e5393b249b8a1"]  # Florida
        },
        "searchText": ""
    }

    try:
        r = requests.post(WORKDAY_API, headers=HEADERS, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []

    jobs = []
    for job in data.get("jobPostings", []):
        location = job.get("locationsText", "Unknown")
        if "Orlando" not in location:
            continue  # Skip non-Orlando jobs

        external_path = job.get("externalPath", "")
        # Extract the job ID from the external path
        job_id = external_path.split("/")[-1]
        # Construct the correct public URL
        link = f"https://fourseasons.wd3.myworkdayjobs.com/en-US/search/job/{job_id}?locationRegionStateProvince=9c1a239b35bd4598856e5393b249b8a1"

        jobs.append({
            "id": job.get("bulletFields", [external_path])[0],
            "title": job.get("title", "Unknown"),
            "location": location,
            "link": link
        })
    return jobs

def send_ntfy(job):
    message = f"📢 New Orlando job posted:\n{job['title']} in {job['location']}\n{job['link']}"
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), timeout=5)
        print(f"✅ Notification sent: {job['title']}")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

def main():
    global seen_jobs
    print("🚀 Starting Four Seasons Orlando Job Alert...")
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

if __name__ == "__main__":
    main()

