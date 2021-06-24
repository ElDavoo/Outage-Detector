import re
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPAuthenticationError


class Mail:

    def __init__(self, sender, receivers, smtp_server, password, port):
        self.sender = sender
        self.receivers = receivers
        self.smtp_server = smtp_server
        self.password = password
        self.port = port

    # Checks if an email is valid
    # Returns None if any email is not valid
    @staticmethod
    def check_mails(mails):
        regex = r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        mail_list = mails.split(',')
        mail_addresses = []
        for mail in mail_list:
            check_result = re.search(regex, mail)
            if not check_result:
                return None
            mail_addresses.append(mail)

        mail_addresses_string = ",".join(mail_addresses)

        return mail_addresses_string

    # Sends an email.
    def send_mail(self, subject, body):
        # Create a multipart message and set headers
        message = MIMEMultipart()
        message["From"] = self.sender
        message["To"] = self.receivers
        message["Subject"] = subject
        message["Bcc"] = self.receivers  # Recommended for mass emails

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        text = message.as_string()

        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        with SMTP_SSL(self.smtp_server, self.port, context=context) as server:
            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receivers.split(','), text)
