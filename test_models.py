import json
import os
from collections import Counter
audit_base = ".agent/data_storage/saida/auditoria"
models = Counter()
for root, _, files in os.walk(audit_base):
    for f in files:
        if f.endswith(".json"):
            try:
                with open(os.path.join(root, f)) as af:
                    data = json.load(af)
                    metrics = data.get("inference_metrics", {})
                    mod = metrics.get("model", "unknown")
                    models[mod] += 1
            except Exception as e:
                print("Error:", e)
print("Models:", models)
