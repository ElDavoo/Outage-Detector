import socket


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
                if self.mail is not None:
                    if x["Subject"] is not None:
                        self.mail.send_mail(x["Subject"], x["Body"])
                if self.google is not None:
                    if x["Subject"] is None:
                        self.google.append(x["Body"])
                self.queue.remove(x)

    def send(self, subject, body):
        self.queue.append({"Subject": subject, "Body": body})
        self.real_send()
