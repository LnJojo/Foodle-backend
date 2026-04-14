from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Génère un lien de vérification qui pointe vers le frontend React
        plutôt que vers une URL Django backend.
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost')
        return f"{frontend_url}/verify-email/{emailconfirmation.key}"

    def format_email_subject(self, subject):
        """Supprime le préfixe [example.com] ajouté par allauth."""
        return subject
