from pathlib import Path
import subprocess
for path in sorted(Path('.').glob('*.js')):
    subprocess.run(['node', '--check', str(path)], check=True)
print('Frontend syntax passed')
