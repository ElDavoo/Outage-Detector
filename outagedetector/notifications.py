import socket

from google.auth.exceptions import TransportError
from gspread.exceptions import APIError
from requests import ReadTimeout, ConnectionError


class Notifications:
    @staticmethod
    def check_tcp():
        try:
            sock = socket.create_connection(
                ("www.google.com", 80))  # if connection to google fails, we assume internet is down
            sock.close()
            return True
        except OSError:
            pass
        return False

    def __init__(self, mail, google):
        self.queue = list()
        self.mail = mail
        self.google = google

    def real_send(self):
        for x in self.queue:
            if Notifications.check_tcp():
                ok = False
                if self.mail is not None:
                    if x["Subject"] is not None:
                        try:
                            self.mail.send_mail(x["Subject"], x["Body"])
                            ok = True
                        except (TransportError, ConnectionError, ReadTimeout):
                            print("Error while sending email.")
                if self.google is not None:
                    if x["Subject"] is None:
                        try:
                            self.google.append(x["Body"].split(','))
                            ok = True
                        except (TransportError, ConnectionError, ReadTimeout, APIError):
                            print("Error while updating GSheet.")
                if ok:
                    self.queue.remove(x)

    def send(self, subject, body):
        self.queue.append({"Subject": subject, "Body": body})
        self.real_send()
