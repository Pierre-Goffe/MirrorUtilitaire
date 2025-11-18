import requests
from bs4 import BeautifulSoup
import subprocess
import os
import shutil  

MIRROR_URL = "https://mirror.sharlio.fr/"


def _get_soup(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"ERREUR: Impossible de joindre {url}. {e}")
        return None
    
def list_dirs(url, exclude=False, exclude_dot_numbers=False):
    soup = _get_soup(url)
    if not soup:
        return []
    dirs = [a.text.strip('/') for a in soup.find_all('a') if a.text.endswith('/')]
    if exclude_dot_numbers:
        dirs = [d for d in dirs if not any(f".{i}" in d for i in range(10))]
    if exclude:
        dirs = [d for d in dirs if not d.startswith('.') and d not in ('assets', 'favicon.ico','project') and "stable" not in d]
    return dirs

def list_os():
    print("Récupération des os disponibles")
    soup = _get_soup(MIRROR_URL)
    if soup is None:
        return []
    
    dirs = [a.text.strip('/') for a in soup.find_all('a') if a.text.endswith('/')]
    dirs = [d for d in dirs if not d.startswith('.') and d not in ('assets', 'favicon.ico')]
    return dirs

def _parse_rsync_progress(line, percent_callback):
    try:
        parts = line.split()
        for part in parts:
            if part.endswith('%') and len(part) > 1:
                pct = int(part[:-1])
                if percent_callback:
                    percent_callback(pct)
                return 
    except:
        pass 

def _parse_debmirror_progress(line, pool_started, percent_callback):
    new_pool_started = pool_started
    try:
        if not pool_started and "pool/" in line:
            new_pool_started = True
            if percent_callback: percent_callback(1) 
        
        if new_pool_started and "%" in line:
            pct_str = line.split("%")[0].split()[-1]
            pct = int(float(pct_str))
            if percent_callback: percent_callback(pct)
    except:
        pass
    return new_pool_started

def get_temp_dir(name: str) -> str:
    home = os.path.expanduser("~")
    base_temp = os.path.join(home, ".cache", "sharlio-mirror-temp")
    os.makedirs(base_temp, exist_ok=True)

    temp_path = os.path.join(base_temp, name)
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
    os.makedirs(temp_path, exist_ok=True)

    return temp_path


def manage_alma_download(os_name, distri, path, rsync_user, text_callback=None, percent_callback=None):
    target_dir = f"{path}/{os_name}/{distri}" 
    os.makedirs(target_dir, exist_ok=True)
    source = f"rsync://{rsync_user}@mirror.sharlio.fr/{os_name}/{distri}/"
    
    
    cmd = ["rsync", "-rlt",  "--partial", "--partial-dir=.rsync-partial", "--append-verify","--no-inplace", "--progress", source, target_dir]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    
    for line in process.stdout:
        line = line.strip()
        if text_callback:
            text_callback(line)
        _parse_rsync_progress(line, percent_callback)

    process.wait()
    if text_callback:
        text_callback(f"{os_name}/{distri} terminé.")
    if percent_callback:
        percent_callback(100)


def manage_debian_download(os_name, distri, path, rsync_user, text_callback=None, percent_callback=None):
    final_dest = os.path.join(path, os_name, distri)
    os.makedirs(final_dest, exist_ok=True)

    temp_dest = get_temp_dir(f"debmirror-debian-{distri}")

    if text_callback:
        text_callback(f"--- Début Debian {distri} ---")
        text_callback(f"[Étape 1/2] Téléchargement vers {temp_dest}")

    cmd_debmirror = [
        "debmirror",
        temp_dest,
        f"--host={rsync_user}@mirror.sharlio.fr",
        "--root=debian",
        "--method=rsync",
        f"--dist={distri}",
        "--section=main,non-free,non-free-firmware",
        "--arch=amd64",
        "--source",
        "--i18n",
        "--ignore-release-gpg",
        "--progress",
        "--exclude=aircrack",
        "--exclude=aircrack-ng"
    ]

    process = subprocess.Popen(
        cmd_debmirror,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace"
    )

    pool_started = False
    if percent_callback:
        percent_callback(0)

    for line in process.stdout:
        line = line.strip()
        if text_callback:
            text_callback(line)
        pool_started = _parse_debmirror_progress(line, pool_started, percent_callback)

    process.wait()

    if process.returncode != 0:
        if text_callback:
            text_callback(f" ERREUR Debmirror (code {process.returncode}) – arrêt.")
        shutil.rmtree(temp_dest, ignore_errors=True)
        return

    if text_callback:
        text_callback(f"[Étape 2/2] Synchronisation vers {final_dest}")

    cmd_rsync = [
        "rsync", "-rlt", "--delete",
        "--no-inplace", "--partial", "--append-verify",
        f"{temp_dest}/",
        f"{final_dest}/"
    ]

    rsync_process = subprocess.Popen(
        cmd_rsync,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace"
    )

    for line in rsync_process.stdout:
        if text_callback:
            text_callback(line.strip())

    rsync_process.wait()

    shutil.rmtree(temp_dest, ignore_errors=True)

    if text_callback:
        text_callback(f"✔ Miroir Debian {distri} terminé.")
    if percent_callback:
        percent_callback(100)

def manage_proxmox_download(os_name, proxmox_category, debian_dist, path, rsync_user, text_callback=None, percent_callback=None):
    repo_map = {
        "pve": {"root": "proxmox-pve", "section": "pve-no-subscription"},
        "pbs": {"root": "proxmox-pbs", "section": "pbs-no-subscription"},
        "ceph-reef": {"root": "proxmox-ceph-reef", "section": "no-subscription"},
        "ceph-squid": {"root": "proxmox-ceph-squid", "section": "no-subscription"}
    }

    if proxmox_category not in repo_map:
        if text_callback: text_callback(f"Catégorie Proxmox inconnue : {proxmox_category}")
        return

    repo_config = repo_map[proxmox_category]
    rsync_module = repo_config["root"]
    section = repo_config["section"]
    
    final_dest = f"{path}/proxmox/{proxmox_category}/{debian_dist}"
    temp_dest = get_temp_dir(f"debmirror-proxmox-{proxmox_category}-{debian_dist}")
    
    if text_callback:
        text_callback(f"\n--- [Proxmox] Sync {proxmox_category} (Dist: {debian_dist}) ---")
        text_callback(f"[Étape 1/2] DL vers temp: {temp_dest}")

    cmd_debmirror = [
        "debmirror", temp_dest,
        f"--host={rsync_user}@mirror.sharlio.fr",
        f"--root={rsync_module}", 
        "--method=rsync",
        f"--dist={debian_dist}",
        f"--section={section}",
        "--arch=amd64",
        "--ignore-release-gpg",
        "--exclude=aircrack",
        "--exclude=aircrack-ng",
        "--progress"
    ]

    process = subprocess.Popen(cmd_debmirror, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                               text=True, errors='replace')
    
    pool_started = False
    if percent_callback: percent_callback(0)

    for line in process.stdout:
        line = line.strip()
        if text_callback: text_callback(line)
        pool_started = _parse_debmirror_progress(line, pool_started, percent_callback)
    
    process.wait()
    if process.returncode != 0:
        if text_callback: text_callback(f"ERREUR sur {proxmox_category} {debian_dist} (code {process.returncode}).")
        shutil.rmtree(temp_dest, ignore_errors=True)
        return 

    if text_callback:
        text_callback(f"[Étape 2/2] Synchro vers: {final_dest}")

    os.makedirs(final_dest, exist_ok=True)

    cmd_rsync = [
        "rsync", "-rlt", "--delete", "--no-inplace", "--partial", "--append-verify",
        f"{temp_dest}/", f"{final_dest}/"
    ]

    rsync_process = subprocess.Popen(cmd_rsync, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    for line in rsync_process.stdout:
        if text_callback:
            text_callback(line.strip())
    rsync_process.wait()

    shutil.rmtree(temp_dest, ignore_errors=True)

    if text_callback:
        text_callback(f"✔ Miroir Proxmox {proxmox_category} ({debian_dist}) terminé.")
    if percent_callback:
        percent_callback(100)


def manage_rocky_download(os_name, distri, path, rsync_user, text_callback=None, percent_callback=None):
    target_dir = f"{path}/{os_name}/{distri}" 
    os.makedirs(target_dir, exist_ok=True)
    
    source = f"rsync://{rsync_user}@mirror.sharlio.fr/{os_name}/{distri}/"
    
    cmd = ["rsync", "-rlt",  "--partial", "--partial-dir=.rsync-partial", "--append-verify","--no-inplace", "--progress", source, target_dir]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
    
    for line in process.stdout:
        line = line.strip()
        if text_callback:
            text_callback(line)
        _parse_rsync_progress(line, percent_callback)
    
    process.wait()
    if text_callback:
        text_callback(f"{os_name}/{distri} terminé.")
    if percent_callback:
        percent_callback(100)


def main():
    print("Test")
if __name__ == "__main__":
    main()