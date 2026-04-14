import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    """
    Backend email Django qui utilise l'API HTTP de Resend.
    Contourne les restrictions SMTP des hébergeurs cloud (ports 25/465/587 bloqués).
    """

    def open(self):
        resend.api_key = settings.RESEND_API_KEY

    def close(self):
        pass

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        self.open()
        sent = 0

        for message in email_messages:
            try:
                # Construit le corps du mail (HTML ou texte brut)
                if message.alternatives:
                    html_body = next(
                        (content for content, mimetype in message.alternatives
                         if mimetype == 'text/html'),
                        None
                    )
                else:
                    html_body = None

                params = {
                    "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": message.to,
                    "subject": message.subject,
                    "text": message.body,
                }

                if html_body:
                    params["html"] = html_body

                resend.Emails.send(params)
                sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e

        return sent
