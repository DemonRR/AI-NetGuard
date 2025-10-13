import os
from pathlib import Path
from shutil import copy, copytree
from sysconfig import get_path
from app.common.setting import VERSION

# 假设已经激活了虚拟环境，如果需要在脚本中激活，可以使用 subprocess 模块
# 例如：
# import subprocess
# subprocess.run(['conda', 'activate', 'YOUR_ENV_NAME'], shell=True)

args = [
    'nuitka',
    '--standalone',
    '--assume-yes-for-downloads',
    f'--output-filename=AI-NetGuard-{VERSION}-linux',
    '--enable-plugins=pyside6',
    '--show-memory',
    '--onefile',
    '--clean-cache=all',
    '--show-progress',
    '--output-dir="/workspace/AI-NetGuard/build"',
    '/workspace/AI-NetGuard/main.py'
]

dist_folder = Path("/workspace/AI-NetGuard/build")

copied_site_packages = [
    
]

copied_standard_packages = [
    
]

# run nuitka
os.system(" ".join(args))

# copy site-packages to dist folder
site_packages = Path(get_path('purelib'))

for src in copied_site_packages:
    src = site_packages / src
    dist = dist_folder / src.name

    print(f"Coping site-packages `{src}` to `{dist}`")

    try:
        if src.is_file():
            copy(src, dist)
        else:
            copytree(src, dist)
    except Exception as e:
        print(f"Error copying {src}: {e}")

# copy standard library
for file in copied_standard_packages:
    src = site_packages.parent / file
    dist = dist_folder / src.name

    print(f"Coping stand library `{src}` to `{dist}`")

    try:
        if src.is_file():
            copy(src, dist)
        else:
            copytree(src, dist)
    except Exception as e:
        print(f"Error copying {src}: {e}")