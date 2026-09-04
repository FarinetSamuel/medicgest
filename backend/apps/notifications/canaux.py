"""
Envoi effectif d'une Notification selon son canal.

État réel de chaque canal (pas d'approximation sur ce qui fonctionne) :

- EMAIL : pleinement fonctionnel. Utilise EMAIL_BACKEND (settings.py) —
  "console" par défaut (affiche l'e-mail dans les logs sans l'envoyer),
  ou un vrai backend SMTP si EMAIL_BACKEND/EMAIL_HOST etc. sont réglés
  dans le .env (voir .env.example).

- SMS : l'interface est prête, mais AUCUN fournisseur SMS n'est configuré
  (Twilio, OVHcloud SMS...) car cela nécessite un compte payant et des
  identifiants que je n'ai pas. Tant que SMS_BACKEND_ACTIVE=False (valeur
  par défaut), un SMS est marqué en échec avec un message explicite
  plutôt que silencieusement ignoré ou faussement marqué "envoyé".

- IN_APP : pleinement fonctionnel — la notification existe en base dès sa
  création et est consultable via /api/v1/notifications/, sans envoi actif
  nécessaire.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def envoyer_notification(notification) -> None:
    """Dispatch vers la bonne fonction d'envoi selon le canal, met à jour le statut."""
    from .models import Notification

    if notification.canal == Notification.Canal.EMAIL:
        _envoyer_email(notification)
    elif notification.canal == Notification.Canal.SMS:
        _envoyer_sms(notification)
    elif notification.canal == Notification.Canal.IN_APP:
        _marquer_disponible_in_app(notification)


def _envoyer_email(notification) -> None:
    from .models import Notification

    destinataire_email = notification.destinataire.email
    try:
        send_mail(
            subject=notification.titre,
            message=notification.message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[destinataire_email],
            fail_silently=False,
        )
        notification.statut = Notification.Statut.ENVOYEE
        notification.date_envoi = timezone.now()
    except Exception as exc:  # noqa: BLE001 — on veut capturer toute erreur SMTP
        notification.statut = Notification.Statut.ECHEC
        notification.erreur = str(exc)
        logger.error("Échec d'envoi e-mail pour la notification %s : %s", notification.id, exc)
    notification.save(update_fields=["statut", "date_envoi", "erreur"])


def _envoyer_sms(notification) -> None:
    from .models import Notification

    if not getattr(settings, "SMS_BACKEND_ACTIVE", False):
        notification.statut = Notification.Statut.ECHEC
        notification.erreur = (
            "Aucun fournisseur SMS configuré (SMS_BACKEND_ACTIVE=False). "
            "Un compte Twilio ou OVHcloud SMS (ou équivalent) et ses identifiants "
            "doivent être ajoutés dans .env pour activer ce canal."
        )
        notification.save(update_fields=["statut", "erreur"])
        return

    # Point d'extension pour un vrai fournisseur SMS une fois configuré :
    # appeler ici l'API du fournisseur (ex. Twilio) avec les identifiants
    # lus depuis settings, puis mettre à jour statut/date_envoi/erreur
    # selon la même logique que _envoyer_email ci-dessus.
    raise NotImplementedError(
        "SMS_BACKEND_ACTIVE=True mais aucune intégration fournisseur n'est "
        "encore implémentée ici."
    )


def _marquer_disponible_in_app(notification) -> None:
    from .models import Notification

    notification.statut = Notification.Statut.ENVOYEE
    notification.date_envoi = timezone.now()
    notification.save(update_fields=["statut", "date_envoi"])
