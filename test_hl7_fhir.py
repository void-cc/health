import json
import io

def parse_fhir(file_data):
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
                                "Value": f"{sys}/{dia} mmHg"
                            })
                    else:
                        parsed_fhir_data.append({
                            "Date": date_obj,
                            "Type": "Vitals",
                            "Value": f"{val} {unit}"
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
                            "Normal Max": normal_max
                        })
    return parsed_fhir_data

def parse_hl7(hl7_text):
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
                obs_date = "2023-01-01" # Dummy for testing

            if name and val:
                data.append({
                    "Date": obs_date,
                    "Type": "Blood Test",
                    "Name": name,
                    "Value": val,
                    "Unit": unit,
                    "Normal Min": normal_min,
                    "Normal Max": normal_max
                })
    return data

hl7_data = "OBR|1|||1234^Test|||20231024120000\nOBX|1|NM|GLU^Glucose||100|mg/dL|70-110|N|||F|||20231024123000"
print("HL7:", parse_hl7(hl7_data))

fhir_data = {
  "resourceType": "Bundle",
  "entry": [
    {
      "resource": {
        "resourceType": "Observation",
        "code": { "text": "Glucose" },
        "effectiveDateTime": "2023-01-01T10:00:00Z",
        "valueQuantity": { "value": 5.5, "unit": "mmol/l" },
        "referenceRange": [ { "low": { "value": 3.9 }, "high": { "value": 5.8 } } ]
      }
    }
  ]
}
print("FHIR:", parse_fhir(fhir_data))
