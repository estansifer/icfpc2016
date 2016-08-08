import pytz
import datetime
import time
import requests
import json
import os
import os.path

teamid = 248

url_hello = "http://2016sv.icfpcontest.org/api/hello"
url_blob = "http://2016sv.icfpcontest.org/api/blob/" # apppend the hash
url_snapshot_list = "http://2016sv.icfpcontest.org/api/snapshot/list"
url_submit_problem = "http://2016sv.icfpcontest.org/api/problem/submit" # POST
url_submit_solution = "http://2016sv.icfpcontest.org/api/solution/submit" # POST

def get(url, post = None, filename = None):
    time.sleep(1.001) # minimum 1 second between queries
    apikeyheader = "X-API-Key"
    apikey = "248-b09bb7ee975fa210cd17aa20ad96bccc"

    headers = {
            apikeyheader : apikey,
            "Accept-Encoding" : "gzip"
            }

    if post is None:
        r = requests.get(url, headers = headers)
    else:
        r = requests.post(url, headers = headers, data = post, files = {'solution_spec' : open(filename, 'rb')})

    print (url + ' ' + str(r.status_code))
    try:
        r.raise_for_status()
    except:
        print (r.text)
        raise
    return r

def saveblob(blobhash, filename):
    blob = get(url_blob + blobhash).text
    with open(filename, 'w') as f:
        f.write(blob)

def hello():
    print (get(url_hello).json())

def save_most_recent_snapshot(filename = "snapshot"):
    snapshots = get(url_snapshot_list).json()["snapshots"]

    h = None
    lasttime = None
    for s in snapshots:
        if h is None or lasttime < s["snapshot_time"]:
            h = s["snapshot_hash"]
            lasttime = s["snapshot_time"]

    saveblob(h, filename)

def download_problems(snapshot_file = "snapshot"):
    with open(snapshot_file) as f:
        snapshot = json.load(f)

    problems = snapshot["problems"]

    print ("Iterating over problems")
    print ("Number of problems: " + str(len(problems)))

    i = 0
    for p in problems:

        path = "problems/" + str(p["problem_id"])
        if os.path.isfile(path):
            continue
        if os.path.exists(path):
            raise ValueError("Path " + path + " exists but is not a file")

        i = i + 1
        if i > 1000:
            print ("Too many requests, did 1000 of " + str(len(problems)) + ".")
            return

        try:
            saveblob(p["problem_spec_hash"], path)
        except:
            print ("Failed to write to " + path + ".")
            os.remove(path)
        else:
            print ("Saved to " + path + " .")

# valid values for hour is 0 through 45 inclusive, or None to mean all the remaining ones
def publish_problem(filename, hour = None):
    def timestamp(h):
        start = 1470441600
        increment = 3600
        return start + h * increment

    if hour is None:
        hours = list(range(46))
    else:
        hours = [hour]

    for h in hours:
        t = timestamp(h)
        t1 = datetime.datetime.fromtimestamp(t, tz = pytz.utc)
        t2 = datetime.datetime.now(tz = pytz.utc)
        if t1 <= t2:
            print ("You missed your chance for hour " + str(h) + "!")
        else:
            r = get(url_submit_problem, {'publish_time' : str(t)}, filename)
            print (r.text)

def unsubmitted_solutions():
    xs = os.listdir("solutions")
    ys = set(os.listdir("submitted"))

    res = []
    for x in xs:
        if x not in ys:
            res.append(int(x))
    return sorted(res)

def submit_solution(pid):
    print("Submitting", pid)
    r = get(url_submit_solution, {'problem_id' : str(pid)}, "solutions/" + str(pid))
    print (r.text)
    open("submitted/" + str(pid), 'a').close()

def submit_solutions():
    for pid in unsubmitted_solutions():
        submit_solution(pid)

if __name__ == "__main__":
    # publish_problem('myproblems/example')
    # save_most_recent_snapshot()
    # download_problems()
    submit_solutions()
