##############
### IMPORT ###
import os
import re
import sys
import platform
import json
import subprocess
from datetime import datetime

##################
### OS CHECKUP ###
osType = platform.system()
if osType == "Windows":
    anydeskPath = r"C:\ProgramData\AnyDesk"
    anydeskConfFile = rf"{anydeskPath}\system.conf"
    logDir = rf"{anydeskPath}\logs"
    os.makedirs(logDir, exist_ok=True)
    logFile = rf"{logDir}\pushAnydeskIDtoGLPI_log.txt"
    if not os.path.exists(logFile):
        open(logFile, "w").close()

if osType == "Linux":
    logFile = r"/var/log/perso/pushAnydeskIDtoGLPI_log.txt"
    if not os.path.exists(logFile):
        open(logFile, "w").close()

def log(message):
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    with open(logFile, "a", encoding="utf-8") as f:
        f.write(log_entry)

def installer_requests():
    print("Tentative d'installation du module 'requests'")
    log("Tentative d'installation du module 'requests'")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        print("Le module 'requests' a été installé avec succès.")
        log("Le module 'requests' a été installé avec succès.")
    except subprocess.CalledProcessError:
        print("Échec de l'installation de 'requests'.")
        log("Échec de l'installation de 'requests'.")
    import requests


log("### Début du script ###")

#######################
### ANYDESK CHECKUP ###
if osType == "Windows":
    if not os.path.exists(anydeskConfFile):
        print(f"Le fichier {anydeskConfFile} est introuvable.")
        log(f"Le fichier {anydeskConfFile} est introuvable.")
        sys.exit(1)

    with open(anydeskConfFile, "r", encoding="utf-8") as f:
        for ligne in f:
            if re.match(r"^ad\.anynet\.id=", ligne):
                match = re.search(r"\d+", ligne)
                if match:
                    anydeskId = match.group()
                    break

    if not anydeskId:
        print("L'ID AnyDesk est introuvable.")
        log("L'ID AnyDesk est introuvable.")
        sys.exit(1)

if osType == "Linux":
    try:
        anydeskId = subprocess.run(['anydesk', '--get-id'], capture_output=True, check=True).stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"Erreur de commande : {e}")
        log(f"Erreur de commande : {e}")
        print("stderr :", e.stderr.decode())
        log("stderr :", e.stderr.decode())
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        log(f"Erreur inattendue : {e}")

################
### GLPI API ###
computerName = platform.node()
glpiUrl = "https://URL/apirest.php"
appToken = "appToken"
userToken = "userToken"

### IMPORT OR INSTALL REQUESTS ###
try:
    import requests
    print("Le module 'requests' est installé.")
    log("Le module 'requests' est installé.")
except ImportError:
    print("Le module 'requests' n'est pas installé.")
    log("Le module 'requests' n'est pas installé.")
    installer_requests()

initHeaders = {
    "Content-Type": "application/json",
    "Authorization": f"user_token {userToken}",
    "App-Token": f"{appToken}"
}

### GET INIT SESSION TOKEN ###
try:
    requestsGetInit = requests.get(f"{glpiUrl}/initSession", headers=initHeaders)
    requestsGetInit.raise_for_status()
    sessionToken = requestsGetInit.json().get("session_token")
    if not sessionToken:
        raise ValueError("Token de session non reçu.")
        log("Token de session non reçu.")
except Exception as e:
    print(f"Erreur pendant l'initialisation de session API : {e}")
    log(f"Erreur pendant l'initialisation de session API : {e}")
    sys.exit(1)

sessionHeaders = {
    "Content-Type": "application/json",
    "Session-Token": f"{sessionToken}",
    "App-Token": f"{appToken}"
}

### GET COMPUTER ID ###
try:
    requestsGet = requests.get(f"{glpiUrl}/Computer/?expand_dropdowns=true&searchText[name]={computerName}", headers=sessionHeaders)
    requestsGet.raise_for_status()
    requestsResult = requestsGet.json()
    computerId = requestsResult[0]["id"]
    if not computerId:
        raise ValueError("Computer ID non trouvé.")
        log("Computer ID non trouvé.")
except Exception as e:
    print(f"Erreur pendant la récuperation de la liste des pc : {e}")
    log(f"Erreur pendant la récuperation de la liste des pc : {e}")
    sys.exit(1)

updateBody = {
    "input": {
        "comment": f"AnyDesk ID: {anydeskId}"
    }
}

### PUT ANYDESK ID TO COMPUTER COMMENTS ###
try:
    requestsPut = requests.put(f"{glpiUrl}/Computer/{computerId}", headers=sessionHeaders, json=updateBody)
    requestsPut.raise_for_status()
    print(f"Le champ Comments du pc {computerName} ID : {computerId} a bien été mis à jour.")
    log(f"Le champ Comments du pc {computerName} ID : {computerId} a bien été mis à jour.")
except Exception as e:
    print(f"Erreur pendant l'importation dans GLPI : {e}")
    log(f"Erreur pendant l'importation dans GLPI : {e}")

### KILL SESSION ###
try:
    requestsPut = requests.get(f"{glpiUrl}/killSession", headers=sessionHeaders)
    requestsPut.raise_for_status()
    print("la session est terminée.")
    log("la session est terminée.")
except Exception as e:
    print(f"Erreur pendant la fermeture de session : {e}")
    log(f"Erreur pendant la fermeture de session : {e}")

log("### Fin du script ###")
