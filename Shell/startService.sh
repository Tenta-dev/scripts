#!/bin/bash

SERVICES_TO_CHECK="exempleService" # services séparé par un espace

echo "Démarrage de la vérification et du démarrage des services..."

for SERVICE_NAME in $SERVICES_TO_CHECK; do
    echo "---"
    echo "Vérification du service : $SERVICE_NAME"

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "Le service '$SERVICE_NAME' est déjà en cours d'exécution (actif)."
    else
        echo "Le service '$SERVICE_NAME' est arrêté ou inactif."
        echo "Tentative de démarrage du service '$SERVICE_NAME'..."
        sudo systemctl start "$SERVICE_NAME"

        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "Le service '$SERVICE_NAME' a été démarré avec succès."
        else
            echo "Échec du démarrage du service '$SERVICE_NAME'."
            echo "Veuillez vérifier les logs avec 'journalctl -xeu $SERVICE_NAME' pour plus de détails."
        fi
    fi
done

echo "---"
echo "Traitement de tous les services terminé."
exit 0
