import sys, os
sys.path.append(os.path.abspath("."))
from scripts.generate_progress import generate_dashboard
import scripts.generate_progress
scripts.generate_progress.generate_dashboard()
# We will just read the generated HTML and extract TOTAL_
with open(".agent/data_storage/PROGRESS.html") as f:
    text = f.read()
import re
print("Pendentes:", re.search(r'Pendentes[^0-9]*([0-9]+)', text).group(1) if re.search(r'Pendentes[^0-9]*([0-9]+)', text) else "Not found")
print("Total processado:", re.search(r'Total processado[^0-9]*([0-9]+)', text).group(1) if re.search(r'Total processado[^0-9]*([0-9]+)', text) else "Not found")
