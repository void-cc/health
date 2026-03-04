"""
Tests for HL7 parsing logic (no Django dependency required).

Run directly:   python test_parsing.py
Import safely:  import test_parsing
"""

import unittest


def parse_hl7(hl7_text):
    """Parse HL7 v2 message text and return a list of observation dicts."""
    data = []
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
                data.append({
                    "Date": obs_date,
                    "Type": "Blood Test",
                    "Name": name,
                    "Value": val,
                    "Unit": unit,
                    "Normal Min": normal_min,
                    "Normal Max": normal_max,
                })
    return data


class HL7ParsingTests(unittest.TestCase):
    """Unit tests for the HL7 v2 parser."""

    HL7_BASIC = (
        "OBR|1|||1234^Test|||20231024120000\n"
        "OBX|1|NM|GLU^Glucose||100|mg/dL|70-110|N|||F|||20231024123000"
    )

    def test_basic_observation_parsed(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(len(data), 1)

    def test_observation_name(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Name"], "Glucose")

    def test_observation_value(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Value"], "100")

    def test_observation_unit(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Unit"], "mg/dL")

    def test_observation_normal_min(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Normal Min"], 70.0)

    def test_observation_normal_max(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Normal Max"], 110.0)

    def test_date_from_obr(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Date"], "2023-10-24")

    def test_date_from_obx_field_15(self):
        hl7 = (
            "OBR|1|||||||20230101000000\n"
            "OBX|1|NM|HGB^Hemoglobin||14|g/dL|13-17|N|||F|||20231115080000"
        )
        data = parse_hl7(hl7)
        self.assertEqual(data[0]["Date"], "2023-11-15")

    def test_name_without_caret(self):
        hl7 = "OBX|1|NM|Glucose||90|mg/dL|70-110"
        data = parse_hl7(hl7)
        self.assertEqual(data[0]["Name"], "Glucose")

    def test_missing_ref_range_leaves_none(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|"
        data = parse_hl7(hl7)
        self.assertIsNone(data[0]["Normal Min"])
        self.assertIsNone(data[0]["Normal Max"])

    def test_invalid_ref_range_leaves_none(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|normal"
        data = parse_hl7(hl7)
        self.assertIsNone(data[0]["Normal Min"])
        self.assertIsNone(data[0]["Normal Max"])

    def test_empty_message_returns_empty(self):
        self.assertEqual(parse_hl7(""), [])

    def test_multiple_observations(self):
        hl7 = (
            "OBR|1|||||||20231024120000\n"
            "OBX|1|NM|GLU^Glucose||100|mg/dL|70-110\n"
            "OBX|2|NM|HGB^Hemoglobin||14|g/dL|13-17"
        )
        data = parse_hl7(hl7)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1]["Name"], "Hemoglobin")

    def test_type_is_blood_test(self):
        data = parse_hl7(self.HL7_BASIC)
        self.assertEqual(data[0]["Type"], "Blood Test")

    def test_fallback_date_when_no_obr(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|70-110"
        data = parse_hl7(hl7)
        self.assertEqual(data[0]["Date"], "2023-01-01")

    def test_carriage_return_separator(self):
        hl7 = "OBR|1|||||||20231024120000\rOBX|1|NM|GLU^Glucose||100|mg/dL|70-110"
        data = parse_hl7(hl7)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Name"], "Glucose")


if __name__ == '__main__':
    unittest.main()
