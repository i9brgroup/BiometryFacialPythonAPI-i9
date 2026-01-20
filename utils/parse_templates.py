import json
import os

current_dir = os.path.dirname(__file__)
templates_path = os.path.join(current_dir, 'templates.json')
with open(templates_path, 'r', encoding='utf-8') as f:
    templates_json = json.load(f)

def normalize_templates(obj):
    templates = []
    if isinstance(obj, list):
        for item in obj:
            templates.extend(normalize_templates(item))
        return templates
    if isinstance(obj, dict):
        if 'embedding_base64' in obj:
            return [obj]
        if 'data' in obj:
            return normalize_templates(obj['data'])
        for key in ('templates', 'items', 'results'):
            if key in obj:
                return normalize_templates(obj[key])
        for v in obj.values():
            templates.extend(normalize_templates(v))
        return templates
    return []

normalized = normalize_templates(templates_json)
print(f"Found {len(normalized)} templates")
for i,t in enumerate(normalized):
    tid = t.get('id') or t.get('name') or t.get('subject') or t.get('user_id') or f"template_{i}"
    print(i, tid, 'det_score=' + str(t.get('det_score')))

