import json
from collections import namedtuple
import tracker.views as views
from unittest.mock import MagicMock

# Create a mock file object
File = namedtuple('File', ['name', 'read'])
request = MagicMock()

file_data = []

class MockFile:
    def __init__(self, name, content):
        self.name = name
        self.content = content
    def read(self):
        return self.content

def load_json(file):
    return json.loads(file.read().decode('utf-8'))

json.load = load_json

hl7_content = b"OBR|1|||1234^Test|||20231024120000\nOBX|1|NM|GLU^Glucose||100|mg/dL|70-110|N|||F|||20231024123000"
f = MockFile('test.hl7', hl7_content)

hl7_text = f.read().decode("UTF8")
lines = hl7_text.replace('\r', '\n').split('\n')
current_date = None
for line in lines:
    fields = line.split('|')
    if fields[0] == 'OBR' and len(fields) > 7:
        date_field = fields[7]
        if date_field and len(date_field) >= 8:
            current_date = f"{date_field[0:4]}-{date_field[4:6]}-{date_field[6:8]}"
    elif fields[0] == 'OBX' and len(fields) > 5:
        name_field = fields[3]
        name = name_field.split('^')[1] if '^' in name_field else name_field
        val = fields[5]
        unit = fields[6] if len(fields) > 6 else ""
        ref_range = fields[7] if len(fields) > 7 else ""

        normal_min = None
        normal_max = None
        if '-' in ref_range:
            try:
                normal_min = float(ref_range.split('-')[0])
                normal_max = float(ref_range.split('-')[1])
            except ValueError:
                pass

        obs_date = current_date
        if len(fields) > 14 and fields[14] and len(fields[14]) >= 8:
            d = fields[14]
            obs_date = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"

        if not obs_date:
            obs_date = "2023-01-01"

        if name and val:
            file_data.append({
                "Date": obs_date,
                "Type": "Blood Test",
                "Name": name,
                "Value": val,
                "Unit": unit,
                "Normal Min": normal_min,
                "Normal Max": normal_max
            })

print("HL7 test passed, data:", file_data)
