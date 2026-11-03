"""Read-only freshness check; updating the baseline requires reviewing the affected claims."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tele-claude', required=True, type=Path, help='Tele-Claude source checkout')
args = parser.parse_args()
here = Path(__file__).resolve().parent
roots = {'charter': here.parents[2], 'tele-claude': args.tele_claude.resolve()}
record = json.loads((here / 'sources.json').read_text())
changed = []
for source in record['sources']:
    root = roots[source['repo']]
    if source.get('ref'):
        result = subprocess.run(['git', '-C', str(root), 'show',
                                 f"{source['ref']}:{source['path']}"], capture_output=True)
        digest = hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else 'missing'
    else:
        path = root / source['path']
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'missing'
    if digest != source['sha256']:
        changed.append(f"{source['repo']}:{source['path']}" +
                       (f" (ref {source['ref']})" if source.get('ref') else ''))
if changed:
    print('Review changed sources before refreshing the baseline:\n' + '\n'.join(changed))
    raise SystemExit(1)
print(f"All {len(record['sources'])} reviewed source hashes match. This checks freshness, not correctness.")
