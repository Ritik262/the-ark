import mailchimp_transactional
from mailchimp_transactional.api_client import ApiClientError
import re
import traceback

EMAIL_REGEX = r"^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*" \
              r"@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$"


class EmailClient(object):
    """
    Class that posts messages a Mandrill account
    """
    def __init__(self, api_key):
        """
        Setting up the Email connection with the Mandrill token in the configuration file.
        """
        self.mandrill_client = mailchimp_transactional.Client(api_key)

    def send_email(self, from_email, to_emails, message, subject="A Message From The Ark", sender_name="The Ark"):
        email_details = {
            "from_email": from_email,
            "from_name": sender_name,
            "subject": subject,
            "html": message,
            "to": [{"email": email, "type": "to"} for email in to_emails]
        }

        # Check parameters for validity
        error_message = "Email Configuration problem occurred while sending your email | "
        if not re.match(EMAIL_REGEX, from_email):
            raise EmailClientException(f"{error_message} The 'FROM' email {from_email!r} is not a valid email address",
                                       traceback.format_exc(), email_details)
        if type(to_emails) is not list:
            raise EmailClientException(f"{error_message} The to_emails parameter is not a List object",
                                       traceback.format_exc(), email_details)
        for email in to_emails:
            if not re.match(EMAIL_REGEX, email):
                raise EmailClientException(f"{error_message} The 'TO' email {email!r} is not a valid email address.",
                                           traceback.format_exc(),
                                           email_details)

        # Attempt to send the email
        try:
            response = self.mandrill_client.messages.send({'message': email_details})
            if response[0]["status"] == "rejected".lower():
                raise response
        except ApiClientError as mandrill_exception:
            message = f"Mandrill Error occurred while attempting to send your email | {mandrill_exception}"
            raise EmailClientException(message, traceback.format_exc(), email_details)


class EmailClientException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(EmailClientException, self).__init__()

    def __str__(self):
        exception_msg = "Email Client Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"{self.stacktrace}"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg