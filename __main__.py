import datetime
import http.server
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile

world_tag_regex = re.compile("<WORLD>(.+?)</WORLD>")
worlds = {"Reset": 0, "Watopia": 1, "Richmond": 2, "London": 3, "New York": 4, "Innsbruck": 5, "Bologna TT": 6,
          "Yorkshire": 7, "Crit City": 8, "Makuri Islands": 9, "France": 10, "Paris": 11}


def change_world(world_id, prefs_path):
    try:
        f = open(prefs_path, "r")
        content = f.read()
        f.close()

        m = world_tag_regex.search(content)
        if m is not None:
            i1 = content.find("<WORLD>") + len("<WORLD>")
            i2 = content.find("</WORLD>")
            new_content = content[0:i1] + str(world_id) + content[i2:]
        else:
            if world_id == -1:
                return
            i = content.find("<ZWIFT>") + len("<ZWIFT>")
            new_content = content[0:i] + f"\n    <WORLD>{world_id}</WORLD>" + content[i:]

        f = open(prefs_path, "w")
        f.write(new_content)
        f.close()
        return True
    except Exception as err:
        print(f"Error during change_world: {err}", file=sys.stderr)
        return False


def extract_webpage():
    zip_path = pathlib.Path(__file__).parent

    dir_path = tempfile.mkdtemp()
    archive = zipfile.ZipFile(zip_path, "r")
    for f in archive.namelist():
        if f.startswith("webpage/"):
            archive.extract(f, path=pathlib.Path(dir_path))

    return dir_path


def find_prefs_file():
    path = pathlib.Path.home().joinpath("documents\\Zwift\\prefs.xml")
    print(path.absolute())
    if path.exists() and path.is_file():
        return path
    else:
        return None


def get_target_world():
    if len(sys.argv) > 1:
        try:
            world_id = int(sys.argv[1])
            if world_id in worlds.values():
                return world_id
        except Exception as err:
            print("Invalid world id passed.", file=sys.stderr)
            print(err, file=sys.stderr)

    print("Starting interactive mode.")
    tmp_dir = extract_webpage()

    s: http.server.HTTPServer
    msg = []
    heartbeat = [datetime.datetime.now()]

    def shutdown():
        time.sleep(3)
        s.shutdown()

    class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=tmp_dir + "/webpage/", **kwargs)

        def do_HEAD(self):
            heartbeat[0] = datetime.datetime.now()

        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            msg.append(post_data)
            self.send_response(200)
            self.end_headers()
            threading.Thread(target=shutdown).start()

        def log_message(self, format, *args):
            return

    def heartbeat_check():
        while len(msg) == 0:
            if datetime.datetime.now() > heartbeat[0] + datetime.timedelta(seconds=10):
                s.shutdown()
                print("Heartbeat timeout", file=sys.stderr)
                return
            time.sleep(1)

    threading.Thread(target=heartbeat_check).start()

    s = http.server.HTTPServer(("localhost", 21899), MyRequestHandler)
    webbrowser.open("http://localhost:21899/")
    s.serve_forever(1)

    j = json.loads(msg[0])
    world_id = int(j["world_id"])

    shutil.rmtree(tmp_dir)

    print("World ID: " + str(world_id))
    return world_id


def os_check():
    return os.name == "nt"


if not os_check():
    print("This tool requires windows.", file=sys.stderr)
    sys.exit(1)

p = find_prefs_file()
if p is None:
    print("Could not find prefs.xml file in documents\\Zwift\\", file=sys.stderr)
    sys.exit(1)

w = get_target_world()
if w is None or w not in worlds.values():
    print(f"Invalid world id: {w}!", file=sys.stderr)
    sys.exit(1)

if change_world(w, p):
    sys.exit(0)
else:
    sys.exit(1)
