import json
import base64
import numpy as np
import os

current_dir = os.path.dirname(__file__)
templates_path = os.path.join(current_dir, 'templates.json')

with open(templates_path, 'r', encoding='utf-8') as f:
    templates_json = json.load(f)

# Extract data (handle object or list)
data = templates_json.get('data') if isinstance(templates_json, dict) else templates_json
if isinstance(data, list):
    templates_list = data
elif isinstance(data, dict):
    templates_list = [data]
else:
    raise SystemExit('Formato inesperado em templates.json')

if not templates_list:
    raise SystemExit('Nenhum template encontrado')

base_template = templates_list[0]
base_emb_b64 = base_template.get('embedding_base64')
if base_emb_b64 is None:
    raise SystemExit("Template não contém 'embedding_base64'")

base_bytes = base64.b64decode(base_emb_b64)
base_emb = np.frombuffer(base_bytes, dtype=np.float32)
# normalize
base_emb = base_emb / (np.linalg.norm(base_emb) + 1e-9)

rng = np.random.default_rng(seed=42)
perturbed = base_emb + rng.normal(0, 0.05, size=base_emb.shape).astype(np.float32)
perturbed = perturbed / (np.linalg.norm(perturbed) + 1e-9)

random_vec = rng.normal(0, 1.0, size=base_emb.shape).astype(np.float32)
random_vec = random_vec / (np.linalg.norm(random_vec) + 1e-9)

def cosine(a, b):
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))

results = {
    'self_similarity': cosine(base_emb, base_emb),
    'perturbed_similarity': cosine(base_emb, perturbed),
    'random_similarity': cosine(base_emb, random_vec)
}

print(json.dumps({'status': 'success', 'data': results}, indent=2))

