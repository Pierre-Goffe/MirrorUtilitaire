# Sharlio Linux Mirror Utility



## 📌 Introduction

Cet utilitaire permet de créer et mettre à jour automatiquement des miroirs locaux de distributions Linux depuis la source **Sharlio**.

Conçu spécifiquement pour **WSL (Windows Subsystem for Linux)**, il offre une **interface graphique (GUI) en Python/PyQt5** pour sélectionner les distributions et piloter les outils de synchronisation sous-jacents (**rsync** et **debmirror**) sans gérer de commandes complexes.

### Distributions supportées :
* ✅ **Proxmox**
* ✅ **Debian**
* ✅ **AlmaLinux**
* ✅ **RockyLinux**

---

## Architecture du projet

```text
SharlioUtilsRepo/
├── app.py               # Point d'entrée de l'interface (PyQt5)
├── widgets.py           # Composants graphiques
├── mirror_util.py       # Moteur de synchro (rsync, parsing HTML)
├── SharlioLogo.ico      # Icône de l'application
├── apt_packages.txt     # Liste des dépendances système (Debian/Ubuntu)
├── pip_packages.txt     # Liste des dépendances Python
└── README.md
```

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