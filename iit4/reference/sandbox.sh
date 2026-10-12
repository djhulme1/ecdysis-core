#!/bin/sh
# Install the wheels offline into /tmp/site, add a stub dist-info for PyPhi (it reads its own version at import), run.
set -e
pip install --quiet --no-index --find-links /wheels --target /tmp/site numpy==1.26.4 scipy==1.13.1 pandas==2.2.3 Graphillion==2.1 networkx==3.4.2 joblib more_itertools ordered-set psutil pyyaml tblib toolz tqdm >/dev/null 2>&1
mkdir -p /tmp/site/pyphi-2.0.0a1.dist-info
printf 'Metadata-Version: 2.1\nName: pyphi\nVersion: 2.0.0a1\n' > /tmp/site/pyphi-2.0.0a1.dist-info/METADATA
cd /work
PYTHONPATH=/tmp/site:/src/pyphi:/src/graphiit python3 /scripts/pyphi_ref.py
