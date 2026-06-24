# Installation des jobs de notification CodeRoute Guinée

## Prérequis

- Systemd ≥ 232
- Utilisateur `coderoute` avec accès à `/opt/coderoute`
- Backend déployé sur `/opt/coderoute/backend`

## Installation

```bash
# Copier les fichiers
sudo cp /opt/coderoute/scripts/systemd/coderoute-cron.sh /opt/coderoute/scripts/
sudo chmod +x /opt/coderoute/scripts/coderoute-cron.sh
sudo mkdir -p /var/log/coderoute
sudo chown coderoute: /var/log/coderoute

# Installer les units (service template + timers)
sudo cp coderoute-notifications.service /etc/systemd/system/coderoute-notifications@.service
sudo cp coderoute-exam-reminder-24h.timer /etc/systemd/system/
sudo cp coderoute-exam-reminder-2h.timer /etc/systemd/system/
sudo cp coderoute-payment-pending.timer /etc/systemd/system/

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable --now coderoute-exam-reminder-24h.timer
sudo systemctl enable --now coderoute-exam-reminder-2h.timer
sudo systemctl enable --now coderoute-payment-pending.timer
```

## Vérification

```bash
# Voir l'état des timers
systemctl list-timers coderoute-*

# Voir les logs
journalctl -u coderoute-notifications@exam_reminder_24h -f
tail -f /var/log/coderoute/cron.log
```

## Déclencher manuellement (test)

```bash
# Via systemd
systemctl start coderoute-notifications@exam_reminder_24h

# Ou directement
/opt/coderoute/scripts/coderoute-cron.sh exam_reminder_24h

# Ou via l'API admin
curl -X POST "https://api.coderoute.gov.gn/api/v1/dashboard/notifications/run-job?job=exam_reminder_24h" \
  -H "Authorization: Bearer <token>"
```

## Fréquences configurées

| Job | Fréquence | Description |
|---|---|---|
| exam_reminder_24h | Toutes les 2h (6h–18h) | Rappel candidats dont examen est dans 22–26h |
| exam_reminder_2h | Toutes les 30min | Rappel candidats dont examen est dans 1h30–2h30 |
| payment_pending_7d | Tous les jours 09h00 | Relance paiements en attente > 7 jours |
