##############
### IMPORT ###
import os
from datetime import datetime
import platform
import subprocess
import sys
import re

##################
### OS CHECKUP ###
osType = platform.system()

if osType == "Windows":
    logDir = r"C:\ProgramData\changeME\logs\"
    os.makedirs(logDir, exist_ok=True)
    logFile = rf"{logDir}\pushDocksToGlpi_log.txt"
    if not os.path.exists(logFile):
        open(logFile, "w").close()

if osType == "Linux":
    logFile = r"/var/log/changeME/pushDocksToGlpi_log.txt"
    if not os.path.exists(logFile):
        open(logFile, "w").close()

def log(message):
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    with open(logFile, "a", encoding="utf-8") as f:
        f.write(log_entry)
log("### Début du script ###")
try:
    import requests
    print("Le module 'requests' est installé.")
    log("Le module 'requests' est installé.")
except ImportError:
    print("Le module 'requests' n'est pas installé.")
    log("Le module 'requests' n'est pas installé.")
    sys.exit(1)

#######################
### DOCK ET GLPI CHECKUP ###
glpiUrl = "changeME"
if osType == "Linux":
    try:
        cmd = "fwupdmgr get-devices --json | jq -r '.Devices[] | select(.Plugin == \"dell_dock\") | .Serial //empty' | awk -F'/' '{print$1}'"
        try:
            dockSerial = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True).stdout.strip().splitlines()[1]
        except:
            dockSerial = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True).stdout.strip().splitlines()[0]
        cmd = "fwupdmgr get-devices --json | jq -r '.Devices[] | select(.Plugin == \"dell_dock\") | .Name //empty' | awk -F'/' '{print$1}'"
        dockModel = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    except subprocess.CalledProcessError as e:
        print(f"Erreur de commande : {e}")
        log(f"Erreur de commande : {e}")
        print("stderr :", e.stderr)
        log("stderr :", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue durant la récupération des infos de la dock station: {e}")
        log(f"Erreur inattendue durant la récupération des infos de la dock station: {e}")
        sys.exit(1)

if osType == "Windows":
    try:
        cmd = r'Get-CimInstance -Namespace root\dcim\sysman -ClassName DCIM_Chassis | Where-Object { $_.CreationClassName -like "DCIM_DockingStation" } | Select-Object -ExpandProperty Tag'
        dockSerial = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True, check=True).stdout.strip()
        cmd = r'Get-CimInstance -Namespace root\dcim\sysman -ClassName DCIM_Chassis | Where-Object { $_.CreationClassName -like "DCIM_DockingStation" } | Select-Object -ExpandProperty Name'
        dockModel = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Erreur de commande : {e}")
        log(f"Erreur de commande : {e}")
        print("stderr :", e.stderr)
        log("stderr :", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue durant la récupération des infos de la dock station: {e}")
        log(f"Erreur inattendue durant la récupération des infos de la dock station: {e}")
        sys.exit(1)


if osType == "Linux":
    try:
        cmd = ["ping", "-c", "1", glpiUrl]
        pingResult = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Ping vers '{glpiUrl}' réussi : l'hôte est joignable.")
        log(f"Ping vers '{glpiUrl}' réussi : l'hôte est joignable.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur de commande : {e}")
        log(f"Erreur de commande : {e}")
        print("stderr :", e.stderr)
        log("stderr :", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue durant le ping GLPI: {e}")
        log(f"Erreur inattendue durant le ping GLPI: {e}")
        sys.exit(1)

if osType == "Windows":
    try:
        cmd = ["ping", "-n", "1", glpiUrl]
        pingResult = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Ping vers '{glpiUrl}' réussi : l'hôte est joignable.")
        log(f"Ping vers '{glpiUrl}' réussi : l'hôte est joignable.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur de commande : {e}")
        log(f"Erreur de commande : {e}")
        print("stderr :", e.stderr)
        log("stderr :", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue durant le ping GLPI: {e}")
        log(f"Erreur inattendue durant le ping GLPI: {e}")
        sys.exit(1)

################
### GLPI API ###
glpiApiUrl = "https://changeME/apirest.php"
appToken = "changeME"
userToken = "changeME"

initHeaders = {
    "Content-Type": "application/json",
    "Authorization": f"user_token {userToken}",
    "App-Token": f"{appToken}"
}

### GET INIT SESSION TOKEN ###
try:
    requestsGetInit = requests.get(f"{glpiApiUrl}/initSession", headers=initHeaders)
    requestsGetInit.raise_for_status()
    sessionToken = requestsGetInit.json().get("session_token")
    if not sessionToken:
        raise ValueError("Token de session non reçu.")
except Exception as e:
    print(f"Erreur pendant l'initialisation de session API : {e}")
    log(f"Erreur pendant l'initialisation de session API : {e}")
    sys.exit(1)

sessionHeaders = {
    "Content-Type": "application/json",
    "Session-Token": f"{sessionToken}",
    "App-Token": f"{appToken}"
}

### DEF ###
def incrementNom(nom):
    match = re.search(r'(\D*-DK)(\d+)', nom)
    if match:
        prefix = match.group(1)
        number = int(match.group(2)) + 1
        new_nom = f"{prefix}{number:03}"  # Conserve le format sur 3 chiffres
        return new_nom
    else:
        raise ValueError("Format de nom invalide")

def compareNom(nom1, nom2):
    match1 = re.search(r'(\D*-DK)(\d+)', nom1)
    match2 = re.search(r'(\D*-DK)(\d+)', nom2)
    if match1 and match2:
        number1 = int(match1.group(2))
        number2 = int(match2.group(2))
        if not number2 == number1 + 1:
            return False
    else:
        raise ValueError("Format de nom invalide")

def getModelId(nom):
    requestsGet = requests.get(f"{glpiApiUrl}/PeripheralModel?range=0-1000&expand_dropdowns=true&searchText[name]={nom}", headers=sessionHeaders)
    requestsGet.raise_for_status()
    requestsResult = requestsGet.json()[0]["id"]
    return requestsResult

def isDeleted(name):
    requestsGetDeleted = requests.get(f"{glpiApiUrl}/peripheral/?expand_drodpowns=true&is_deleted=true&sort=name&range=0-1000&searchText[peripheraltypes_id]=2&searchText[name]={name}", headers=sessionHeaders)
    requestsGetDeleted.raise_for_status()
    requestsResult = requestsGetDeleted.json()
    return isinstance(requestsResult, (dict, list)) and not requestsResult

### GET DOCK DATAS ###
try:
    requestsGet = requests.get(f"{glpiApiUrl}/peripheral/?expand_drodpowns=true&range=0-1000&searchText[peripheraltypes_id]=2&searchText[serial]={dockSerial}", headers=sessionHeaders)
    requestsGet.raise_for_status()
    requestsResult = requestsGet.json()
    dockId = requestsResult[0]["id"]
    print(f"La dock station portant le numero de serie ({dockSerial}) éxiste sous l'ID: {dockId}")
    log(f"La dock station portant le numero de serie ({dockSerial}) éxiste sous l'ID: {dockId}")
except Exception as e:
    if isinstance(e, IndexError):
        try:
            requestsGet = requests.get(f"{glpiApiUrl}/peripheral/?expand_drodpowns=true&is_deleted=true&range=0-1000&searchText[peripheraltypes_id]=2&searchText[serial]={dockSerial}", headers=sessionHeaders)
            requestsGet.raise_for_status()
            requestsResult = requestsGet.json()
            dockId = requestsResult[0]["id"]
            print(f"La dock station portant le numero de serie ({dockSerial}) éxiste sous l'ID: {dockId} dans les périphériques supprimés.")
            log(f"La dock station portant le numero de serie ({dockSerial}) éxiste sous l'ID: {dockId} dans les périphériques supprimés.")
        except Exception as e:
            if isinstance(e, IndexError):
                print(f"La dock station portant le numero de serie ({dockSerial}) n'éxiste pas.")
                log(f"La dock station portant le numero de serie ({dockSerial}) n'éxiste pas.")
                ### GET NEW DOCK NAME ###
                try:
                    requestsGet = requests.get(f"{glpiApiUrl}/peripheral/?expand_drodpowns=true&sort=name&range=0-1000&searchText[peripheraltypes_id]=2", headers=sessionHeaders)
                    requestsGet.raise_for_status()
                    requestsResult = requestsGet.json()
                    dock1Name = None
                    dock2Name = None
                    newDockName = None
                    for docks in requestsResult:
                        if dock1Name == None:
                            dock1Name = docks["name"]
                            continue
                        if dock2Name == None:
                            dock2Name = docks["name"]
                            continue
                        if compareNom(dock1Name, dock2Name) == False:
                            newDockName = incrementNom(dock1Name)
                            if isDeleted(newDockName):
                                break
                            else:
                                newDockName = None
                        else:
                            dock1Name = dock2Name
                            dock2Name = docks["name"]
                        if docks["name"] == requestsGet.json()[-1]["name"]:
                            newDockName = incrementNom(requestsGet.json()[-1]["name"])
                            while isDeleted(newDockName) == False:
                                newDockName = incrementNom(newDockName)
                            break
                    print(newDockName)
                    sys.exit(1)
                except Exception as e:
                    print(f"Erreur pendant la récupération de la list des dock stations: {e}")
                    log(f"Erreur pendant la récupération de la list des dock stations: {e}")
                    sys.exit(1)

                ### GET DOCK MODEL ID ###
                try:
                    dockModelId = getModelId(dockModel)
                except Exception as e:
                    print(f"le model de dock stations ({dockModel}) n'est pas présent dans GLPI: {e}")
                    log(f"le model de dock stations ({dockModel}) n'est pas présent dans GLPI: {e}")
                    ### POST DOCK MODEL ###
                    try:
                        createBody = {
                        "input": {
                            "name": f"{dockModel}",
                            "weight": 0,
                            "required_units": 1,
                            "depth": 1,
                            "power_connections": 0,
                            "power_consumption": 0,
                            "is_half_rack": 0
                            }
                        }
                        requestsPost = requests.post(f"{glpiApiUrl}/PeripheralModel/", headers=sessionHeaders, json=createBody)
                        requestsPost.raise_for_status()
                        print(requestsPost.text)
                        log(requestsPost.text)
                        print(f"Le model de dock station {dockModel} a bien été importé.")
                        log(f"Le model de dock station {dockModel} a bien été importé.")
                        dockModelId = getModelId(dockModel)
                    except Exception as e:
                        print(f"Erreur pendant l'importation dans GLPI : {e}")
                        log(f"Erreur pendant l'importation dans GLPI : {e}")
                        sys.exit(1)

                updateBody = {
                    "input": {
                        "name": f"{newDockName}",
                        "users_id_tech": 50,
                        "serial": f"{dockSerial}",
                        "locations_id": 36,
                        "peripheraltypes_id": 2,
                        "peripheralmodels_id": f"{dockModelId}",
                        "manufacturers_id": 278,
                        "states_id": 3
                    }
                }
                ### POST DOCK DATAS ###
                try:
                    requestsPost = requests.post(f"{glpiApiUrl}/peripheral/", headers=sessionHeaders, json=createBody)
                    requestsPost.raise_for_status()
                    print(requestsPost.text)
                    log(requestsPost.text)
                    print(f"La dock station {newDockName} portant le numéro de série {dockSerial} a bien été importé.")
                    log(f"La dock station {newDockName} portant le numéro de série {dockSerial} a bien été importé.")
                except Exception as e:
                    print(f"Erreur pendant l'importation dans GLPI : {e}")
                    log(f"Erreur pendant l'importation dans GLPI : {e}")
                    sys.exit(1)
            else:
                print(f"une erreur est survenue pendant la récupération de la dock station ({dockSerial}): {e}")
                log(f"une erreur est survenue pendant la récupération de la dock station ({dockSerial}): {e}")
                sys.exit(1)
    else:
        print(f"une erreur est survenue pendant la récupération de la dock station ({dockSerial}): {e}")
        log(f"une erreur est survenue pendant la récupération de la dock station ({dockSerial}): {e}")
        sys.exit(1)

### KILL SESSION ###
try:
    requestsPut = requests.get(f"{glpiApiUrl}/killSession", headers=sessionHeaders)
    requestsPut.raise_for_status()
    print("la session est terminée.")
    log("la session est terminée.")
except Exception as e:
    print(f"Erreur pendant la fermeture de session : {e}")
    log(f"Erreur pendant la fermeture de session : {e}")

log("### Fin du script ###")
