# Sharlio Linux Mirror Utility

## 📌 Introduction

Cet utilitaire WSL permet de récupérer automatiquement plusieurs distributions Linux depuis le miroir **Sharlio**.  
Il fournit une **interface graphique Python (PyQt5)** pour sélectionner les distributions et lancer leur téléchargement via **rsync** ou **debmirror**.

Distributions supportées :

- **Proxmox**
- **Debian**
- **AlmaLinux**
- **RockyLinux**

L’objectif est de simplifier le téléchargement de miroir en évitant les commandes manuelles pour l'utilisateur.

---

## 🏗️ Architecture générale
SharlioUtilsRepo/
├── app.py               # Application principale (PyQt5)
├── widgets.py           # Widgets PyQt5
├── mirror_util.py       # Fonctions utilitaires (rsync, parsing HTML, etc.)
├── SharlioLogo.ico
└── README.md
├── apt_packages.txt         # Dépendances APT pour WSL Debian
└── pip_packages.txt         # Dépendances Python (PyPI)


### 🔎 Note

L'application utilise :

- **PyQt5** pour l’interface  
- **rsync** pour le téléchargement principal  
- **debmirror** pour le téléchargement Debian 
- **BeautifulSoup** pour l'analyse des pages du miroir HTTP  

Ces composants nécessitent une installation complète sous WSL.

---

## 🛠️ Préparation de l’environnement WSL

### ⚠️ Notes importantes

- L'application doit être **exécutée dans WSL**, pas dans Windows directement.  
- Il est recommandé d’utiliser **Debian WSL** pour maximiser la compatibilité.  
- L’utilitaire nécessite un accès réseau.  

---

## 📥 Prérequis

### 🔹 Côté Windows (PowerShell Admin)

Installer WSL :

```powershell
wsl --install Debian
```

### 🔹 Côté WSL (Debian)
Mise à jour et installer les dépendances apt
```bash
sudo apt update && sudo apt upgrade -y
cd SharlioUtilRepo/
sed -i 's/\r$//' apt_packages.txt
xargs -a apt_packages.txt sudo apt install -y
```
Activer un environnement virtuel et installer les dépendances pythons
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip_packages.txt
```

## 🚀 Lancement de l’application sur WSL avec python
Lancer l’application :
```bash
python3 app.py
```