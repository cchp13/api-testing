
"""
A Python script to install the project dependencies.
"""

import argparse
from email.utils import parseaddr
from getpass import getpass
import json
from pathlib import Path
import subprocess
import shutil
import sys

from tests.utils.imap_handler import IMAP_handler

# ========================== CONSTANTS ==========================

DEPENDENCY_MANAGER_PATHS = {
    "win32":{
        "poetry_python_executable": Path(".poetry").absolute() / ".venv" / "Scripts" / "python.exe",
        "poetry_executable": Path(".poetry").absolute() / ".venv" / "Scripts" / "poetry.exe",
        "project_python_executable": Path(".venv").absolute() / "Scripts" / "python.exe",
        "project_poetry_link": Path(".venv").absolute() / "Scripts" / "poetry.exe",
        "shell": True,
    },
    "linux":{
        "poetry_python_executable": Path(".poetry").absolute() / ".venv" / "bin" / "python",
        "poetry_executable": Path(".poetry").absolute() / ".venv" / "bin" / "poetry",
        "project_python_executable": Path(".venv").absolute() / "bin" / "python",
        "project_poetry_link": Path(".venv").absolute() / "bin" / "poetry",
        "shell": False,
    },
    "common":{
        "project_venv": Path(".venv"),
        "poetry_dir": Path(".poetry"),
        "poetry_venv": Path(".poetry") / ".venv",
        "poetry_cache": Path(".poetry") / ".cache",
    }
}

SECRETS_ROOT = Path("secrets")
SECRETS = {
    "email_credentials": SECRETS_ROOT / "gmail_credentials.json",
    "api_key": SECRETS_ROOT / "fallback_API_key.json",
}


# =========================== INPUTS ============================

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--clear", action="store_true", help="Delete virtual environments and cache folders.")
    parser.add_argument("-C", "--clear-secrets", action="store_true", help="Delete local secrets.")
    return parser.parse_args()


# ========================== FUNCTIONS ==========================

def clear_previous_installation():
    if DEPENDENCY_MANAGER_PATHS["common"]["project_venv"].is_dir():
        print(f"Deleting project virtual environment...", end="", flush=True) 
        shutil.rmtree(DEPENDENCY_MANAGER_PATHS["common"]["project_venv"])
        print("Done.")
    if DEPENDENCY_MANAGER_PATHS["common"]["poetry_dir"].is_dir():
        print(f"Deleting dependency manager virtual environment...", end="", flush=True) 
        shutil.rmtree(DEPENDENCY_MANAGER_PATHS["common"]["poetry_dir"])
        print("Done.")
    pytest_cache = Path(".pytest_cache")
    if pytest_cache.is_dir():
        print(f"Deleting Pytest's cache...", end="", flush=True) 
        shutil.rmtree(pytest_cache)
        print("Done.")


def clear_secrets():
    if SECRETS_ROOT.is_dir():
        print(f"Deleting Secrets...", end="", flush=True) 
        shutil.rmtree(SECRETS_ROOT)
        print(f"Done")


def create_venv(venv: str = ".venv"):
    """Create a virtual environment at the relative path specified."""
    if sys.platform == "linux":
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "virtualenv"],check=True)

    print(f"Creating virtual environment at {venv}...", end="", flush=True) 
    subprocess.run(
        [sys.executable, "-m", "venv", venv], check=True, shell=DEPENDENCY_MANAGER_PATHS[sys.platform]["shell"]
    )
    print("Done.")


def install_poetry():
    create_venv(DEPENDENCY_MANAGER_PATHS["common"]["poetry_venv"])
    executable = DEPENDENCY_MANAGER_PATHS[sys.platform]["poetry_python_executable"]
    subprocess.run(
        [executable, "-m", "pip", "install", "--upgrade", "poetry"],
        check=True,
        shell=DEPENDENCY_MANAGER_PATHS[sys.platform]["shell"]
    )


def link_poetry_to_project():
    poetry_executable = DEPENDENCY_MANAGER_PATHS[sys.platform]["poetry_executable"]
    poetry_link_on_project = DEPENDENCY_MANAGER_PATHS[sys.platform]["project_poetry_link"]
    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-Command",
                "New-Item",
                "-ItemType",
                "HardLink",
                "-Path",
                f"'{poetry_link_on_project.as_posix()}'",
                "-Target",
                f"'{poetry_executable.as_posix()}'",
            ],
            check=True,
        )
    else:
        subprocess.run(["ln", "-sf", poetry_executable, poetry_link_on_project], check=True)


def configure_poetry():
    poetry_executable = DEPENDENCY_MANAGER_PATHS[sys.platform]["project_poetry_link"]
    poetry_cache = DEPENDENCY_MANAGER_PATHS["common"]["poetry_cache"]
    subprocess.run([poetry_executable, "config", "virtualenvs.create", "false", "--local"], check=True)
    subprocess.run([poetry_executable, "config", "virtualenvs.in-project", "true", "--local"], check=True)
    subprocess.run([poetry_executable, "config", "cache-dir", poetry_cache, "--local"], check=True)


def setup_poetry():
    install_poetry()
    link_poetry_to_project()
    configure_poetry()


def install_deps():
    subprocess.run([DEPENDENCY_MANAGER_PATHS[sys.platform]["poetry_executable"], "install"], check=True)
    

def get_email_credentials():
    
    email_credentials_file = SECRETS["email_credentials"]

    # Check if credentials are present from a previous installation.
    if email_credentials_file.is_file():
        email_credentials = json.loads(email_credentials_file.read_text())
        email_address = parseaddr(email_credentials["address"])
        if email_address[1] and email_credentials.get("pswd", ""):
            return
        else:
            print("Stored email credentials not valid.")

    # While this does the job, we could use a Pydantic model for input data validation.
    print("\nPlease provide email credentials for API Key request")
    address = ""
    n = 0
    N = 5
    while not address and n<N:
        address_input = input("gmail address: ")
        address = parseaddr(address_input)[1]
        n+=1
    
    if not address:
        raise Exception("Failed to provide a valid gmail address.")
    
    pswd = getpass(f"Please provide app-password to connect to {address}: ")
    pswd2 = getpass("Please repeat app-password: ")

    if pswd != pswd2:
        raise Exception("Passwords do not match.")

    email_credentials = {"address": address, "pswd": pswd}
    try:
        imap_handler = IMAP_handler(email_credentials=email_credentials)
        assert imap_handler.check()
        print("Email credentials validated.")
    except Exception:
        raise Exception("Failed to connect to IMAP server. Please ensure email credentials are valid.")

    try:
        email_credentials_file.write_text(json.dumps(email_credentials))
        print("Email credentials stored successfully.")
    except Exception:
        raise Exception(f"Failed to store credentials at {email_credentials_file.as_posix()}.")


def main(args):

    if sys.platform not in ["win32", "linux"]:
        raise Exception("Unsupported OS.")
    if sys.version_info[:2] != (3, 12):
        print("WARNING: Developed using Python 3.12. If running into issues with other versions, switch to 3.12.")

    if args.clear:
        clear_previous_installation()

    if args.clear_secrets:
        clear_secrets()

    # Create project virtual environment.
    if not DEPENDENCY_MANAGER_PATHS["common"]["project_venv"].is_dir():
        create_venv(DEPENDENCY_MANAGER_PATHS["common"]["project_venv"])
        
    # Setup dependency manager
    if not DEPENDENCY_MANAGER_PATHS["common"]["poetry_dir"].is_dir():
        setup_poetry()

    # Install dependencies
    install_deps()

    # Ask for email credentials if missing.
    SECRETS_ROOT.mkdir(exist_ok=True, parents=True)
    get_email_credentials()


if __name__ == "__main__":
    main(get_args())
