"""Copy canonical ai sources into Space package. Never copies training artifacts."""
import shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for folder in ['api','runtime','schemas','detection','evidence']:
    for source in (root/'ai'/folder).glob('*.py'):
        target=root/'huggingface_deployment/ai'/folder/source.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
print('Packaged canonical inference sources. Existing weights were not modified.')
