"""
Tests for HL7 v2 and FHIR Bundle parsing logic (no Django dependency required).

Run directly:   python test_hl7_fhir.py
Import safely:  import test_hl7_fhir
"""

import unittest


# ---------------------------------------------------------------------------
# Pure parsing helpers (mirrors the logic in tracker/views.py import_data)
# ---------------------------------------------------------------------------

def parse_hl7(hl7_text):
    """Parse an HL7 v2 message and return a list of observation dicts."""
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


def parse_fhir(file_data):
    """Parse a FHIR R4 Bundle dict and return a list of observation dicts."""
    parsed_fhir_data = []
    if isinstance(file_data, dict) and file_data.get('resourceType') == 'Bundle':
        for entry in file_data.get('entry', []):
            obs = entry.get('resource', {})
            if obs.get('resourceType') == 'Observation':
                name = obs.get('code', {}).get('text')
                if not name:
                    codings = obs.get('code', {}).get('coding', [])
                    if codings:
                        name = codings[0].get('display')

                val_quantity = obs.get('valueQuantity', {})
                val = val_quantity.get('value')
                unit = val_quantity.get('unit')

                date_str = obs.get('effectiveDateTime')
                date_obj = date_str[:10] if date_str else None

                ref_ranges = obs.get('referenceRange', [])
                normal_min = None
                normal_max = None
                if ref_ranges:
                    normal_min = ref_ranges[0].get('low', {}).get('value')
                    normal_max = ref_ranges[0].get('high', {}).get('value')

                is_vital = False
                categories = obs.get('category', [])
                for cat in categories:
                    codings = cat.get('coding', [])
                    for c in codings:
                        if c.get('code') == 'vital-signs':
                            is_vital = True

                if is_vital:
                    if name and "Blood Pressure" in name and "component" in obs:
                        sys = None
                        dia = None
                        for comp in obs['component']:
                            c_name = comp.get('code', {}).get('text', '').lower()
                            c_val = comp.get('valueQuantity', {}).get('value')
                            if 'systolic' in c_name:
                                sys = c_val
                            elif 'diastolic' in c_name:
                                dia = c_val
                        if sys and dia:
                            parsed_fhir_data.append({
                                "Date": date_obj,
                                "Type": "Vitals",
                                "Value": f"{sys}/{dia} mmHg",
                            })
                    else:
                        parsed_fhir_data.append({
                            "Date": date_obj,
                            "Type": "Vitals",
                            "Value": f"{val} {unit}",
                        })
                else:
                    if name and val is not None and date_obj:
                        parsed_fhir_data.append({
                            "Date": date_obj,
                            "Type": "Blood Test",
                            "Name": name,
                            "Value": val,
                            "Unit": unit,
                            "Normal Min": normal_min,
                            "Normal Max": normal_max,
                        })
    return parsed_fhir_data


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class HL7ParserTests(unittest.TestCase):
    """Tests for the HL7 v2 parser."""

    HL7_BASIC = (
        "OBR|1|||1234^Test|||20231024120000\n"
        "OBX|1|NM|GLU^Glucose||100|mg/dL|70-110|N|||F|||20231024123000"
    )

    def test_single_observation_returned(self):
        self.assertEqual(len(parse_hl7(self.HL7_BASIC)), 1)

    def test_name_from_caret_field(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Name"], "Glucose")

    def test_value(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Value"], "100")

    def test_unit(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Unit"], "mg/dL")

    def test_normal_min(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Normal Min"], 70.0)

    def test_normal_max(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Normal Max"], 110.0)

    def test_date_derived_from_obr(self):
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Date"], "2023-10-24")

    def test_date_from_obx_field_15(self):
        hl7 = (
            "OBR|1|||||||20230101000000\n"
            "OBX|1|NM|HGB^Hemoglobin||14|g/dL|13-17|N|||F|||20231115080000"
        )
        self.assertEqual(parse_hl7(hl7)[0]["Date"], "2023-11-15")

    def test_name_without_caret(self):
        hl7 = "OBX|1|NM|Glucose||90|mg/dL|70-110"
        self.assertEqual(parse_hl7(hl7)[0]["Name"], "Glucose")

    def test_missing_ref_range(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|"
        row = parse_hl7(hl7)[0]
        self.assertIsNone(row["Normal Min"])
        self.assertIsNone(row["Normal Max"])

    def test_non_numeric_ref_range(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|normal"
        row = parse_hl7(hl7)[0]
        self.assertIsNone(row["Normal Min"])
        self.assertIsNone(row["Normal Max"])

    def test_empty_message(self):
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
        self.assertEqual(parse_hl7(self.HL7_BASIC)[0]["Type"], "Blood Test")

    def test_fallback_date_when_no_obr(self):
        hl7 = "OBX|1|NM|GLU^Glucose||100|mg/dL|70-110"
        self.assertEqual(parse_hl7(hl7)[0]["Date"], "2023-01-01")

    def test_carriage_return_separator(self):
        hl7 = "OBR|1|||||||20231024120000\rOBX|1|NM|GLU^Glucose||100|mg/dL|70-110"
        data = parse_hl7(hl7)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Name"], "Glucose")


class FHIRParserTests(unittest.TestCase):
    """Tests for the FHIR R4 Bundle parser."""

    BLOOD_TEST_BUNDLE = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "Glucose"},
                    "effectiveDateTime": "2023-01-01T10:00:00Z",
                    "valueQuantity": {"value": 5.5, "unit": "mmol/l"},
                    "referenceRange": [
                        {"low": {"value": 3.9}, "high": {"value": 5.8}}
                    ],
                }
            }
        ],
    }

    VITAL_BUNDLE = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "Heart Rate"},
                    "effectiveDateTime": "2023-06-01T08:00:00Z",
                    "valueQuantity": {"value": 72, "unit": "bpm"},
                    "category": [
                        {
                            "coding": [
                                {"code": "vital-signs",
                                 "system": "http://terminology.hl7.org/CodeSystem/observation-category"}
                            ]
                        }
                    ],
                }
            }
        ],
    }

    BP_BUNDLE = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "Blood Pressure"},
                    "effectiveDateTime": "2023-06-01T08:00:00Z",
                    "category": [
                        {"coding": [{"code": "vital-signs"}]}
                    ],
                    "component": [
                        {
                            "code": {"text": "Systolic Blood Pressure"},
                            "valueQuantity": {"value": 120},
                        },
                        {
                            "code": {"text": "Diastolic Blood Pressure"},
                            "valueQuantity": {"value": 80},
                        },
                    ],
                }
            }
        ],
    }

    def test_blood_test_parsed(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(len(data), 1)

    def test_blood_test_name(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Name"], "Glucose")

    def test_blood_test_value(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Value"], 5.5)

    def test_blood_test_unit(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Unit"], "mmol/l")

    def test_blood_test_date(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Date"], "2023-01-01")

    def test_blood_test_normal_min(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Normal Min"], 3.9)

    def test_blood_test_normal_max(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Normal Max"], 5.8)

    def test_blood_test_type(self):
        data = parse_fhir(self.BLOOD_TEST_BUNDLE)
        self.assertEqual(data[0]["Type"], "Blood Test")

    def test_vital_sign_parsed(self):
        data = parse_fhir(self.VITAL_BUNDLE)
        self.assertEqual(len(data), 1)

    def test_vital_sign_type(self):
        data = parse_fhir(self.VITAL_BUNDLE)
        self.assertEqual(data[0]["Type"], "Vitals")

    def test_vital_sign_value_format(self):
        data = parse_fhir(self.VITAL_BUNDLE)
        self.assertEqual(data[0]["Value"], "72 bpm")

    def test_vital_sign_date(self):
        data = parse_fhir(self.VITAL_BUNDLE)
        self.assertEqual(data[0]["Date"], "2023-06-01")

    def test_blood_pressure_components(self):
        data = parse_fhir(self.BP_BUNDLE)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Value"], "120/80 mmHg")
        self.assertEqual(data[0]["Type"], "Vitals")

    def test_empty_bundle(self):
        bundle = {"resourceType": "Bundle", "entry": []}
        self.assertEqual(parse_fhir(bundle), [])

    def test_not_a_bundle(self):
        self.assertEqual(parse_fhir({"resourceType": "Patient"}), [])

    def test_non_dict_input(self):
        self.assertEqual(parse_fhir([]), [])

    def test_coding_display_fallback(self):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {
                            "coding": [{"display": "Cholesterol"}]
                        },
                        "effectiveDateTime": "2023-03-01T00:00:00Z",
                        "valueQuantity": {"value": 4.8, "unit": "mmol/l"},
                    }
                }
            ],
        }
        data = parse_fhir(bundle)
        self.assertEqual(data[0]["Name"], "Cholesterol")

    def test_missing_ref_range_leaves_none(self):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {"text": "Glucose"},
                        "effectiveDateTime": "2023-01-01T00:00:00Z",
                        "valueQuantity": {"value": 5.0, "unit": "mmol/l"},
                    }
                }
            ],
        }
        data = parse_fhir(bundle)
        self.assertIsNone(data[0]["Normal Min"])
        self.assertIsNone(data[0]["Normal Max"])

    def test_observation_without_value_skipped(self):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {"text": "Glucose"},
                        "effectiveDateTime": "2023-01-01T00:00:00Z",
                    }
                }
            ],
        }
        self.assertEqual(parse_fhir(bundle), [])

    def test_observation_without_date_skipped(self):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {"text": "Glucose"},
                        "valueQuantity": {"value": 5.0, "unit": "mmol/l"},
                    }
                }
            ],
        }
        self.assertEqual(parse_fhir(bundle), [])


if __name__ == '__main__':
    unittest.main()
