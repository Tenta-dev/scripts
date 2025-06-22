#!/bin/bash

# --- Configuration Générale ---
# Remplacez ces valeurs par vos propres informations
YOUR_DOMAIN="your_domain.com" # Domaine pour GitLab (ex: gitlab.your_domain.com ou l'IP de votre VM)
JIRA_PORT="9000" # Port par défaut de Jira
JIRA_VERSION="9.12.24" # Vérifiez la dernière version sur le site d'Atlassian
# Lien de téléchargement de Jira (à adapter à la version)
JIRA_DOWNLOAD_URL="https://www.atlassian.com/software/jira/downloads/binary/atlassian-jira-software-${JIRA_VERSION}-x64.bin"

# --- Configuration de la base de données Jira (PostgreSQL) ---
JIRA_DB_USER="jiradbuser"
JIRA_DB_PASS="your_jira_db_password" # CHANGEZ CE MOT DE PASSE !
JIRA_DB_NAME="jiradb"
POSTGRES_JDBC_VERSION="42.7.7" # Vérifiez la dernière version du driver JDBC PostgreSQL
POSTGRES_JDBC_DOWNLOAD_URL="https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar"

# --- Fichier de log ---
LOG_FILE="/var/log/jira_gitlab_install.log"

# --- Fonctions utilitaires de logging ---
log_message() {
    local type="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$type] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log_message "INFO" "$1"
}

log_warning() {
    log_message "WARNING" "$1"
}

log_error() {
    log_message "ERROR" "$1"
    exit 1
}

# --- Vérification des prérequis ---
log_info "Initialisation du script d'installation de Jira et GitLab."
log_info "Les logs seront enregistrés dans : $LOG_FILE"

if [[ $EUID -ne 0 ]]; then
   log_error "Ce script doit être exécuté en tant que root (sudo)."
fi

# Redirection de stdout et stderr vers le fichier de log et la console
exec > >(tee -a "$LOG_FILE") 2>&1

# --- 1. Préparation du système Ubuntu ---
log_info "Démarrage de la préparation du système Ubuntu."
{
    apt update && apt upgrade -y
} || log_error "Échec de la mise à jour du système ou de l'installation des paquets."

{
    apt install -y curl wget apt-transport-https ca-certificates software-properties-common
} || log_error "Échec de l'installation des paquets essentiels."
log_info "Préparation du système Ubuntu terminée."

# --- 2. Installation de GitLab Community Edition (CE) ---
log_info "Démarrage de l'installation de GitLab CE."
log_warning "ATTENTION : Postfix ne sera PAS installé. GitLab ne pourra pas envoyer d'emails de notification sans configuration SMTP externe."

log_info "Ajout du dépôt GitLab CE..."
{
    curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | bash
} || log_error "Échec de l'ajout du dépôt GitLab."

log_info "Installation de GitLab CE. Cela peut prendre un certain temps..."
{
    EXTERNAL_URL="http://${YOUR_DOMAIN}" apt install -y gitlab-ce
} || log_error "Échec de l'installation de GitLab CE."

log_info "GitLab est installé. Accédez à http://${YOUR_DOMAIN} dans votre navigateur pour la configuration initiale."
log_info "Vous devrez définir le mot de passe root lors du premier accès."
log_warning "Rappel : Les notifications email ne fonctionneront pas sans configuration SMTP externe."
log_info "Installation de GitLab CE terminée."
echo "---"

# --- 3. Installation de Jira Software ---

log_info "Démarrage de l'installation de Jira Software."

log_info "Installation du JDK (OpenJDK 11) pour Jira..."
{
    apt install -y openjdk-11-jdk
} || log_error "Échec de l'installation du JDK."

log_warning "ATTENTION : Jira sera exécuté par l'utilisateur root ou l'utilisateur courant du script, ce qui n'est PAS recommandé pour la sécurité en production."

log_info "Téléchargement de l'installeur Jira Software ${JIRA_VERSION}..."
{
    wget -O /tmp/atlassian-jira-software-${JIRA_VERSION}-x64.bin "${JIRA_DOWNLOAD_URL}"
} || log_error "Échec du téléchargement de l'installeur Jira. Vérifiez le lien de téléchargement et la version."

log_info "Rendre l'installeur exécutable..."
{
    chmod a+x /tmp/atlassian-jira-software-${JIRA_VERSION}-x64.bin
} || log_error "Échec du changement de permission pour l'installeur Jira."

log_info "Lancement de l'installeur Jira. SUIVEZ ATTENTIVEMENT LES INSTRUCTIONS QUI S'AFFICHERONT :"
log_info "  - Choisir l'option 2 (Custom Install)."
log_info "  - Répertoire d'installation : /opt/atlassian/jira"
log_info "  - Répertoire de données : /var/atlassian/application-data/jira"
log_info "  - Ports : ${JIRA_PORT} (HTTP) et 8005 (Control)"
log_info "  - Installer Jira en tant que service. (Le script activera le service, mais l'installeur peut le demander)."

# Exécuter l'installeur Jira en mode interactif.
# La sortie de l'installeur sera également logguée.
if ! /tmp/atlassian-jira-software-${JIRA_VERSION}-x64.bin; then
    log_error "L'exécution de l'installeur Jira a échoué ou a été interrompue. Veuillez vérifier les logs ci-dessus."
fi
log_info "Installeur Jira terminé (veuillez confirmer qu'il s'est bien déroulé manuellement)."

log_info "Installation et configuration de PostgreSQL pour Jira..."
{
    apt install -y postgresql postgresql-contrib
} || log_error "Échec de l'installation de PostgreSQL."

log_info "Création de la base de données et de l'utilisateur pour Jira dans PostgreSQL..."
{
    sudo -u postgres psql -c "CREATE USER ${JIRA_DB_USER} WITH ENCRYPTED PASSWORD '${JIRA_DB_PASS}';" && \
    sudo -u postgres psql -c "CREATE DATABASE ${JIRA_DB_NAME} OWNER ${JIRA_DB_USER} LC_COLLATE 'C.UTF-8' LC_CTYPE 'C.UTF-8' TEMPLATE template0;" && \
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${JIRA_DB_NAME} TO ${JIRA_DB_USER};"
} || log_error "Échec de la configuration de la base de données Jira dans PostgreSQL."

log_info "Téléchargement du driver JDBC PostgreSQL pour Jira..."
JIRA_LIB_DIR="/opt/atlassian/jira/lib" # Assurez-vous que c'est le bon chemin après l'installation de Jira
{
    wget -O "${JIRA_LIB_DIR}/postgresql-${POSTGRES_JDBC_VERSION}.jar" "${POSTGRES_JDBC_DOWNLOAD_URL}"
} || log_error "Échec du téléchargement du driver JDBC PostgreSQL. Vérifiez le lien et la version."

log_info "Démarrage du service Jira..."
{
    systemctl start jira && systemctl enable jira
} || log_error "Échec du démarrage ou de l'activation du service Jira."

log_info "Jira est installé. Accédez à http://votre_ip_vm:${JIRA_PORT} dans votre navigateur pour la configuration initiale."
log_info "Lors de la configuration de Jira, choisissez 'Ma propre base de données' et entrez les détails PostgreSQL."
log_info "Installation de Jira Software terminée."
echo "---"

# --- 4. Configuration du pare-feu (UFW) ---
log_info "Configuration du pare-feu UFW..."
{
    ufw allow OpenSSH && \
    ufw allow http && \
    ufw allow https && \
    ufw allow ${JIRA_PORT}/tcp && \
    ufw --force enable
} || log_error "Échec de la configuration ou de l'activation du pare-feu UFW."
log_info "Pare-feu configuré. Vérifiez le statut avec 'sudo ufw status'."
echo "---"

log_info "SCRIPT TERMINÉ : Installation et configuration de GitLab et Jira terminées avec succès !"
log_info "N'oubliez pas les étapes post-installation :"
log_info "  - Définir le mot de passe root pour GitLab via l'interface web."
log_info "  - Configurer Jira via l'interface web (base de données, administrateur)."
log_info "  - ENVISAGEZ FORTEMENT de configurer un reverse proxy (Nginx/Apache) avec SSL/TLS pour les deux applications."
log_info "  - Mettre en place une stratégie de sauvegarde robuste."
log_info "  - Surveiller les ressources de votre VM."