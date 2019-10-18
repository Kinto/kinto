import string

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

DEFAULT_EMAIL_SENDER = "admin@example.com"
DEFAULT_SUBJECT_TEMPLATE = "activate your account"
DEFAULT_BODY_TEMPLATE = "{activation-key}"
DEFAULT_CONFIRMATION_SUBJECT_TEMPLATE = "Account active"
DEFAULT_CONFIRMATION_BODY_TEMPLATE = "The account {id} is now active"
DEFAULT_RESET_SUBJECT_TEMPLATE = "Reset password"
DEFAULT_RESET_BODY_TEMPLATE = "{reset-password}"


class EmailFormatter(string.Formatter):
    """Formatter class that will not fail if there's a missing key."""

    def __init__(self, default="{{{0}}}"):
        self.default = default

    def get_value(self, key, args, kwargs):
        return kwargs.get(key, self.default.format(key))


class Emailer:
    def __init__(self, request, user):
        self.request = request
        self.settings = request.registry.settings
        self.user = user
        self.user_email = user["id"]
        self.email_sender = self.settings.get(
            "account_validation.email_sender", DEFAULT_EMAIL_SENDER
        )
        self.mailer = get_mailer(request)

    def send_mail(self, subject_template, body_template, extra_data=None):
        formatter = EmailFormatter()
        if extra_data is None:
            extra_data = {}
        user_email_context = self.user.get("email-context", {})
        # We might have some previous email context.
        try:
            data = self.request.json.get("data", {})
            email_context = data.get("email-context", user_email_context)
        except ValueError:
            email_context = user_email_context

        formatted_subject = formatter.format(
            subject_template, **self.user, **extra_data, **email_context
        )
        formatted_body = formatter.format(
            body_template, **self.user, **extra_data, **email_context
        )
        message = Message(
            subject=formatted_subject,
            sender=self.email_sender,
            recipients=[self.user_email],
            body=formatted_body,
        )
        self.mailer.send(message)

    def send_activation(self, activation_key):
        extra_data = {"activation-key": activation_key}

        subject_template = self.settings.get(
            "account_validation.email_subject_template", DEFAULT_SUBJECT_TEMPLATE
        )
        body_template = self.settings.get(
            "account_validation.email_body_template", DEFAULT_BODY_TEMPLATE
        )
        self.send_mail(subject_template, body_template, extra_data)

    def send_confirmation(self):
        subject_template = self.settings.get(
            "account_validation.email_confirmation_subject_template",
            DEFAULT_CONFIRMATION_SUBJECT_TEMPLATE,
        )
        body_template = self.settings.get(
            "account_validation.email_confirmation_body_template",
            DEFAULT_CONFIRMATION_BODY_TEMPLATE,
        )

        self.send_mail(subject_template, body_template)

    def send_temporary_reset_password(self, reset_password):
        extra_data = {"reset-password": reset_password}
        subject_template = self.settings.get(
            "account_validation.email_reset_password_subject_template",
            DEFAULT_RESET_SUBJECT_TEMPLATE,
        )
        body_template = self.settings.get(
            "account_validation.email_reset_password_body_template", DEFAULT_RESET_BODY_TEMPLATE
        )

        self.send_mail(subject_template, body_template, extra_data)
