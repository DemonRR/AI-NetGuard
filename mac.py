import os
import shutil
import subprocess
from pathlib import Path
from sysconfig import get_path
from app.common.setting import VERSION  # 你项目中的版本定义

# ========================
# 📦 配置项
# ========================
project_root = Path(__file__).parent
main_script = project_root / "main.py"
icon_file = project_root / "app/resource/images/icon.icns"
build_dir = project_root / "build"
output_app_name = f"AI-NetGuard-{VERSION}-mac.app"
output_app_path = build_dir / output_app_name
original_app_path = build_dir / "main.app"

copied_site_packages = [
    # 示例：'requests', 'httpx'
]

copied_stdlib = [
    # 示例：'ssl', 'asyncio'
]

# ========================
# 🚀 构建 Nuitka 命令
# ========================
args = [
    "nuitka",
    "--standalone",
    "--assume-yes-for-downloads",
    "--macos-create-app-bundle",
    f"--macos-app-icon={icon_file}",
    "--enable-plugins=pyside6",
    "--include-package=jiter",
    "--include-package=openai",
    "--show-progress",
    "--remove-output",
    f"--output-dir={build_dir}",
    str(main_script),
]

# ========================
# 🧹 清理旧的构建
# ========================
if output_app_path.exists():
    print(f"🧹 清理旧版本: {output_app_path}")
    shutil.rmtree(output_app_path)

if original_app_path.exists():
    print(f"🧹 清理旧版本: {original_app_path}")
    shutil.rmtree(original_app_path)

# ========================
# 🛠️ 执行 Nuitka 构建
# ========================
print("🔧 开始构建 .app ...")
result = subprocess.run(" ".join(args), shell=True)
if result.returncode != 0:
    print("❌ Nuitka 构建失败")
    exit(1)

# ========================
# 📦 重命名 .app
# ========================
print(f"📦 重命名 main.app 为 {output_app_name}")
original_app_path.rename(output_app_path)

# ========================
# 📁 拷贝依赖 (可选)
# ========================
site_packages = Path(get_path("purelib"))
dist_folder = output_app_path / "Contents" / "MacOS"

for name in copied_site_packages:
    src = site_packages / name
    dst = dist_folder / src.name
    print(f"📦 拷贝第三方依赖: {src} -> {dst}")
    if src.is_file():
        shutil.copy(src, dst)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)

stdlib_path = site_packages.parent
for name in copied_stdlib:
    src = stdlib_path / name
    dst = dist_folder / src.name
    print(f"📦 拷贝标准库模块: {src} -> {dst}")
    if src.is_file():
        shutil.copy(src, dst)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True)

# ========================
# 🔐 设置权限 & 解锁 .app
# ========================
print("🔐 设置权限和解除隔离")
subprocess.run(["chmod", "-R", "+x", str(output_app_path)])
subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(output_app_path)])

print("✅ 打包完成!")
print(f"📂 你的应用位置: {output_app_path}")
