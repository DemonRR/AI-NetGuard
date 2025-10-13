# coding: utf-8
from pathlib import Path

# change DEBUG to False if you want to compile the code to exe
DEBUG = "__compiled__" not in globals()


YEAR = 2025
AUTHOR = "Demon"
VERSION = 'v1.0.1'
date = '2025-3-24'
owner = "DemonRR"
repo = "AI-NetGuard"
HELP_URL = f"https://github.com/{owner}/{repo}/issues"
FEEDBACK_URL = f"https://github.com/{owner}/{repo}/issues"
RELEASE_URL = f"https://github.com/{owner}/{repo}/releases/latest"
LATEST_API = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
STAR_URL = f"https://github.com/{owner}/{repo}"

CONFIG_FOLDER = Path('AppData').absolute()
CONFIG_FILE = CONFIG_FOLDER / "config.json"
