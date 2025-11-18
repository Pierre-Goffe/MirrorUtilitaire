import sys
import os
import shutil
import subprocess
from PyQt5.QtWidgets import QLineEdit, QApplication, QWidget, QMainWindow,QHBoxLayout, QVBoxLayout, QCheckBox, QGridLayout, QFrame, QMessageBox, QFileDialog, QTextEdit , QProgressBar 
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
import widgets
from mirror_util import list_dirs, list_os, manage_alma_download, manage_debian_download, manage_proxmox_download, manage_rocky_download

MIRROR_URL_ALMA = "https://mirror.sharlio.fr/almalinux/"
MIRROR_URL_DEBIAN = "https://mirror.sharlio.fr/debian/dists/"
MIRROR_URL_PROXMOX = "https://mirror.sharlio.fr/proxmox/debian/"
MIRROR_URL_PROXMOX_PVE = "https://mirror.sharlio.fr/proxmox/debian/pve/dists/"
MIRROR_URL_PROXMOX_PBS = "https://mirror.sharlio.fr/proxmox/debian/pbs/dists/"
MIRROR_URL_PROXMOX_CEPH_REEF = "https://mirror.sharlio.fr/proxmox/debian/ceph-reef/dists/"
MIRROR_URL_PROXMOX_CEPH_SQUID = "https://mirror.sharlio.fr/proxmox/debian/ceph-squid/dists/"
MIRROR_URL_ROCKY = "https://mirror.sharlio.fr/rockylinux/"


class DownloadThread(QThread):
    progress_text = pyqtSignal(str)
    progress_percent = pyqtSignal(int)

    def __init__(self, os_name, distri, path, rsync_user):
        super().__init__()
        self.os_name = os_name
        self.distri = distri
        self.path = path
        self.rsync_user = rsync_user

    def run(self):
        if self.os_name == "almalinux":
            manage_alma_download(self.os_name, self.distri, self.path, self.rsync_user, text_callback=self.progress_text.emit,percent_callback=self.progress_percent.emit)
        elif self.os_name == "debian":
            manage_debian_download(self.os_name, self.distri, self.path, self.rsync_user, text_callback=self.progress_text.emit,percent_callback=self.progress_percent.emit)
        elif self.os_name == "proxmox":
            try:
                proxmox_category, debian_dist = self.distri.split(':')
                manage_proxmox_download(self.os_name, proxmox_category, debian_dist, self.path, self.rsync_user, text_callback=self.progress_text.emit,percent_callback=self.progress_percent.emit)
            except ValueError:
                self.progress_text.emit(f"ERREUR: Tâche Proxmox mal formée : {self.distri}")
        elif self.os_name == "rockylinux":
            manage_rocky_download(self.os_name, self.distri, self.path, self.rsync_user, text_callback=self.progress_text.emit,percent_callback=self.progress_percent.emit)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.check = False
        self.os = list_os()
        self.alma = list_dirs(MIRROR_URL_ALMA, exclude=True, exclude_dot_numbers=True)
        self.debian = list_dirs(MIRROR_URL_DEBIAN, exclude=True, exclude_dot_numbers=True)
        self.proxmox = list_dirs(MIRROR_URL_PROXMOX, exclude=True, exclude_dot_numbers=False)
        self.proxmox_pve = list_dirs(MIRROR_URL_PROXMOX_PVE, exclude=True, exclude_dot_numbers=False)
        self.proxmox_pbs = list_dirs(MIRROR_URL_PROXMOX_PBS, exclude=True, exclude_dot_numbers=False)
        self.proxmox_ceph_reef = list_dirs(MIRROR_URL_PROXMOX_CEPH_REEF, exclude=True, exclude_dot_numbers=False)
        self.proxmox_ceph_squid = list_dirs(MIRROR_URL_PROXMOX_CEPH_SQUID, exclude=True, exclude_dot_numbers=False)
        self.rocky = list_dirs(MIRROR_URL_ROCKY, exclude=True, exclude_dot_numbers=True)
        self.launch_download = False
        self.download_dest_path = None

        self.distri_checkboxes = {}

        self.setWindowTitle("Repolio")
        self.setWindowIcon(QIcon('SharlioLogo.ico'))
        copyright_label = widgets.create_label("© 2025 Sharlio. Tous droits réservés.")
        copyright_label.setStyleSheet("color: #888; margin-right: 10px;")
        self.statusBar().addPermanentWidget(copyright_label)

        if not self.check_dependencies():
            QTimer.singleShot(100, self.close)

        self.setup_ui()
    
    def check_dependencies(self):
        """Vérifie que rsync et debmirror sont installés."""
        deps_ok = True
        missing = []

        if shutil.which("rsync") is None:
            missing.append("rsync")
            deps_ok = False
            
        if shutil.which("debmirror") is None:
            missing.append("debmirror")
            deps_ok = False

        if not deps_ok:
            QMessageBox.critical(self, "Dépendances manquantes",
                f"Les paquets suivants sont introuvables : {', '.join(missing)}\n\n"
                "Veuillez les installer avec :\n"
                "sudo apt update && sudo apt install rsync debmirror")
        return deps_ok

    def setup_ui(self):
        # --- Authenfication form ---
        self.auth_widget = QWidget()
        self.setCentralWidget(self.auth_widget)
        auth_layout = QVBoxLayout()
        
        auth_layout.addStretch(1)

        sharlio_label = widgets.create_label("Repolio")
        sharlio_label.setStyleSheet("""
            font-size: 52px;
            font-weight: bold;
            color: #333; /* Une couleur sombre, pas noir pur */
        """)
        sharlio_label.setAlignment(Qt.AlignCenter)
        auth_layout.addWidget(sharlio_label)
        auth_layout.addSpacing(20)
        
        auth_form_layout = QVBoxLayout()
        auth_form_layout.setSpacing(10)
        self.input_user = widgets.create_text_input("Nom d'utilisateur")
        self.input_passwd = widgets.create_text_input("Mot de passe")
        self.input_passwd.setEchoMode(QLineEdit.Password)
        button_connected = widgets.create_button("Se connecter",self.connect_to_repo)
        auth_form_layout.addWidget(self.input_user)
        auth_form_layout.addWidget(self.input_passwd)
        auth_form_layout.addWidget(button_connected)
        
        auth_centering_layout = QHBoxLayout()
        auth_centering_layout.addStretch(1)
        auth_centering_layout.addLayout(auth_form_layout)
        auth_centering_layout.addStretch(1)
        
        auth_layout.addLayout(auth_centering_layout)
        auth_layout.addStretch(1) 
        self.auth_widget.setLayout(auth_layout)

       # --- Choose repositories form ---
        self.choose_repo_widget = QWidget()
        choose_repo_layout = QGridLayout() 
        choose_repo_layout.setContentsMargins(10, 10, 10, 10)

        choose_repo_layout.setColumnStretch(0, 1) 
        choose_repo_layout.setColumnStretch(1, 2)
        choose_repo_layout.setColumnStretch(2, 1)

        self.os_distributions = {
            "almalinux": self.alma,
            "debian": self.debian,
            "proxmox": self.proxmox,
            "rockylinux": self.rocky
        }

        self.list_proxmox = {
            "ceph-reef": self.proxmox_ceph_reef,
            "ceph-squid": self.proxmox_ceph_squid,
            "pbs": self.proxmox_pbs,
            "pve": self.proxmox_pve
        }

        self.distri_layouts = {}
        
        current_row = 0

        for os_name in self.os:
            os_checkbox = QCheckBox(os_name, self)
            
            distri_layout = QVBoxLayout() 
            self.distri_layouts[os_name] = distri_layout

            os_checkbox.stateChanged.connect(lambda state, name=os_name: self.toggle_distributions(name, state))

            choose_repo_layout.addWidget(os_checkbox, current_row, 0, Qt.AlignTop)
            choose_repo_layout.addLayout(distri_layout, current_row, 1, Qt.AlignTop)
            current_row += 1 

            separator = QFrame()
            separator.setFrameShape(QFrame.HLine) 
            separator.setFrameShadow(QFrame.Sunken)
            
            choose_repo_layout.addWidget(separator, current_row, 0, 1, 3) 
            current_row += 1

        button_download = widgets.create_button("Télécharger", self.button_download_pressed)
        choose_repo_layout.addWidget(button_download, current_row, 0)
        choose_repo_layout.setRowStretch(current_row + 1, 1)
        self.choose_repo_widget.setLayout(choose_repo_layout)


    def connect_to_repo(self):
        self.rsync_user = self.input_user.text().strip()
        rsync_pass = self.input_passwd.text().strip()

        if not self.rsync_user or not rsync_pass:
            QMessageBox.warning(self, "Erreur", "L'utilisateur et le mot de passe ne peuvent pas être vides.")
            return
        
        os.environ["RSYNC_PASSWORD"] = rsync_pass

        try:
            cmd = ["rsync", f"rsync://{self.rsync_user}@mirror.sharlio.fr/almalinux"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)     

        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Échec de la connexion", "Authentification refusée. Vérifiez l'utilisateur ou le mot de passe.")
            return 
        except FileNotFoundError:
            QMessageBox.critical(self, "Erreur", "La commande 'rsync' est introuvable.")
            return
        except subprocess.TimeoutExpired:
            QMessageBox.critical(self, "Erreur de connexion", "Le serveur mirror.sharlio.fr ne répond pas (timeout).")
            return
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur inconnue est survenue : {e}")
            return

        self.check = True
        self.show_choose_repo()

    def toggle_distributions(self, os_name, state):
        layout = self.distri_layouts[os_name]
        self.clear_layout(layout)
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.distri_checkboxes[os_name] = {} 
    
        if state == Qt.Checked:
            if os_name == "proxmox":
                for category, dists in self.list_proxmox.items():
                    if not dists:
                        continue 
                    category_label = widgets.create_label(category)
                    category_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
                    layout.addWidget(category_label)
                    
                    category_layout = QHBoxLayout()
                    
                    self.distri_checkboxes[os_name][category] = []
                    
                    for distri in dists:
                        cb = QCheckBox(distri)
                        category_layout.addWidget(cb)
                        self.distri_checkboxes[os_name][category].append(cb)
                    
                    category_layout.addStretch(1) 
                    layout.addLayout(category_layout) 
            
            else:
                distris = self.os_distributions.get(os_name, [])
                self.distri_checkboxes[os_name]['main'] = [] 
                for distri in distris:
                    cb = QCheckBox(distri)
                    layout.addWidget(cb)
                    self.distri_checkboxes[os_name]['main'].append(cb)
    
    def get_selected_distributions(self):
        selected = {}
        for os_name, categories in self.distri_checkboxes.items():
            
            if os_name == "proxmox":
                proxmox_selection = {}
                for category, checkboxes in categories.items():
                    chosen_dists = [cb.text() for cb in checkboxes if cb.isChecked()]
                    if chosen_dists:
                        proxmox_selection[category] = chosen_dists
                if proxmox_selection:
                    selected[os_name] = proxmox_selection
            
            else:
                if 'main' in categories:
                    chosen = [cb.text() for cb in categories['main'] if cb.isChecked()]
                    if chosen:
                        selected[os_name] = chosen
                        
        return selected

    def button_download_pressed(self):
        selected = self.get_selected_distributions()
        if not selected: 
            QMessageBox.information(self, "Aucune sélection", "Veuillez sélectionner au moins un OS et une version.")
            return

        recap_text = "Vous avez sélectionné :\n"

        for os_name, data in selected.items():
            if os_name == "proxmox":
                recap_text += f"- {os_name}:\n"
                for category, dists in data.items():
                    recap_text += f"  - {category}: {', '.join(dists)}\n"
            else:
                recap_text += f"- {os_name} : {', '.join(data)}\n"

        QMessageBox.information(self, "Récapitulatif des sélections", recap_text)

        self.download_dest_path = QFileDialog.getExistingDirectory(
            self, "Choisir un dossier de destination", ""
        )

        if not self.download_dest_path:
            QMessageBox.information(self, "Annulé", "Téléchargement annulé : aucun dossier choisi.")
            return

        self.launch_download = True
        self.download_queue = []
        
        for os_name, data in selected.items():
            if os_name == "proxmox":
                for category, dists in data.items():
                    for deb_dist in dists:
                        self.download_queue.append((os_name, f"{category}:{deb_dist}"))
            else:
                for distri in data:
                    self.download_queue.append((os_name, distri))

        self.download_next()
        print("Dossier de destination :", self.download_dest_path)
        print("Distributions sélectionnées :", selected) 
        print("File d'attente des tâches :", self.download_queue) 

    def show_choose_repo(self):
        self.auth_widget.setParent(None)
        self.setCentralWidget(self.choose_repo_widget)

    def show_progressBar(self, os_name, distri):
        self.progress_widget = QWidget()
        layout = QVBoxLayout()

        log_layout = QHBoxLayout()
        self.show_log_button = widgets.create_button("+", self.toggle_log)
        self.log_visible = False
        log_layout.addWidget(self.show_log_button)
        layout.addLayout(log_layout)

        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setVisible(False)  
        layout.addWidget(self.progress_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("%p%")  
        layout.addWidget(self.progress_bar)

        cancel_button = widgets.create_button("Annuler", self.cancel_download)
        layout.addWidget(cancel_button)

        self.progress_widget.setLayout(layout)
        self.setCentralWidget(self.progress_widget)

        self.thread = DownloadThread(os_name, distri, self.download_dest_path,self.rsync_user)
        self.thread.progress_text.connect(self.update_progress_text)
        self.thread.progress_percent.connect(self.update_progress_percent)
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def cancel_download(self):
        if hasattr(self, "thread") and self.thread.isRunning():
            self.thread.terminate()
            self.progress_text.append("\nTéléchargement annulé.")
            self.progress_bar.setValue(0)

    def clear_layout(self,layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())


    def download_next(self):
        if not self.download_queue:
            self.all_downloads_finished()
            return
        os_name, distri = self.download_queue.pop(0)
        self.show_progressBar(os_name, distri)

    def download_finished(self):
        self.progress_text.append("\nTéléchargement terminé.")
        self.progress_bar.setValue(100)
        QTimer.singleShot(100, self.download_next)

    def toggle_log(self):
        self.log_visible = not self.log_visible
        self.progress_text.setVisible(self.log_visible)
        self.show_log_button.setText("-" if self.log_visible else "+")

    def update_progress_text(self, text):
        self.progress_text.append(text)
        self.progress_text.verticalScrollBar().setValue(
            self.progress_text.verticalScrollBar().maximum()
        )

    def update_progress_percent(self, value):
        self.progress_bar.setValue(value)

    def all_downloads_finished(self):
        QMessageBox.information(self, "Terminé", "Tous les téléchargements sont terminés.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    available_size = screen.availableGeometry().size()
    width = available_size.width()
    height = available_size.height()
    window = MainWindow()
    window.resize(int(width * 0.8), int(height * 0.8))
    window.show()
    sys.exit(app.exec())

