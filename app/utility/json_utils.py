from typing import Optional,Dict
import json

def safe_parse_json(raw: str) -> Optional[Dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except:
        pass
    start = raw.find("{")
    if start == -1:
        return None
    for end in range(start + 1, min(len(raw), start + 5000)):
        if raw[end] == "}":
            try:
                return json.loads(raw[start:end + 1])
            except:
                continue
    return None