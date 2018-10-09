import json
import os


base_path = "storage/"


def save_json_file(file, data):
    with open(base_path + file + ".json", "w") as f:
        json.dump(data, f)

def get_json_file(file):
    try:
        with open(base_path + file + ".json", "r") as f:
            return json.load(f)
    except:
        return None

def delete(file):
    os.remove(base_path + file + ".json")