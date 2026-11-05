"""Read-only OSV advisory lookup for the installed backend dependency closure."""
import importlib.metadata as metadata
import json
from pathlib import Path
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
pending = [Requirement(line) for line in (ROOT / 'backend/requirements.txt').read_text().splitlines()
           if line.strip() and not line.startswith('#')]
packages = {}
while pending:
    requirement = pending.pop()
    if requirement.marker and not requirement.marker.evaluate():
        continue
    name = canonicalize_name(requirement.name)
    if name in packages:
        continue
    try:
        distribution = metadata.distribution(requirement.name)
    except metadata.PackageNotFoundError:
        continue
    packages[name] = distribution.version
    for child in distribution.requires or []:
        parsed = Requirement(child)
        if not parsed.marker or parsed.marker.evaluate():
            pending.append(parsed)

queries = [{'package': {'name': name, 'ecosystem': 'PyPI'}, 'version': version}
           for name, version in sorted(packages.items())]
request = urllib.request.Request('https://api.osv.dev/v1/querybatch',
    data=json.dumps({'queries': queries}).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=45) as response:
    batch = json.load(response)
findings = []
for query, result in zip(queries, batch['results']):
    if result.get('vulns'):
        findings.append({'name': query['package']['name'], 'version': query['version'],
                         'advisory_ids': [v['id'] for v in result['vulns']]})

report = {'source': 'https://api.osv.dev/v1/querybatch', 'installed_packages_checked': len(queries),
          'note': 'Installed dependency closure with default environment markers; optional extras may be omitted. Advisory matches require applicability review.',
          'findings': findings}
(ROOT / 'docs/audit-python-dependencies.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))

def read_advisory(advisory_id):
    with urllib.request.urlopen('https://api.osv.dev/v1/vulns/' + advisory_id, timeout=30) as response:
        return json.load(response)

advisory_ids = sorted({advisory for finding in findings for advisory in finding['advisory_ids'] if advisory.startswith('GHSA-')})
with ThreadPoolExecutor(max_workers=6) as pool:
    advisories = list(pool.map(read_advisory, advisory_ids))
(ROOT / 'docs/audit-python-advisories.json').write_text(json.dumps(advisories, ensure_ascii=False, indent=2), encoding='utf-8')
for advisory in advisories:
    print(advisory['id'] + ': ' + advisory.get('summary', ''))
