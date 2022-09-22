import os
import sys
import socket


class interface:
    def __init__(self):
        self.email_from = None
        self.email_rcpt = []
        self.data = []
        self.scanner = None
        self.connection = None

    def main(self):
        """
            The following two while loops generates text prompt messages to standard
            output to prompt the user to enter the contents of an email message. It
            also takes care of input checking following the requirement from HW1. Note
            that this is not implemented by the client that is used to test against your
            server on Gradescope. Therefore, your server should deal with badly-formed commands
            and data that can trigger 500, 501, 503 errors.
        """
        while True:
            self.scanner = Scanner(safe_input("From: \n"))
            getter = Mailbox("Normal", self.scanner)
            email = getter.email()
            if getter.state == "ERROR":
                print("Error: Wrong Email Format")
                continue
            else:
                self.email_from = email
                self.data.append(f"From: <{email.getter()}>")
                break

        while True:
            """
                Note that this client agent can deal with multiple email recipients, which is 
                not a requirement for this assignment.
            """
            emails = safe_input("To: \n").split(",")
            flag = 0
            for line in emails:
                self.scanner = Scanner(line)
                getter = Mailbox("Normal", self.scanner)
                email = getter.email()
                if getter.state == "ERROR":
                    flag = 1
                    break
                self.email_rcpt.append(email)
            if flag == 1:
                print("Error: Wrong Email Format")
                continue
            else:
                angled_email_list = list(map(lambda x: f"<{x.getter()}>", self.email_rcpt))
                self.data.append(f"To: {', '.join(angled_email_list)}")
                break

        self.data.append("Subject: " + safe_input("Subject: \n"))
        self.data.append("")

        info = safe_input("Message:\n")
        while info != ".":
            self.data.append(info)
            info = safe_input()

        """
            After collecting everything needed, establish socket connection to the server.
        """
        self.smtp()

    """
    Establish socket connection to the server.
    Recieve server response
    Send SMTP commands and email messages. 
    """
    def smtp(self):
        # Establishing socket connection.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.DATASIZE = 256
        server_name = sys.argv[1]
        port_number = int(sys.argv[2])
        host = socket.gethostname()
        server_address = (server_name, port_number)
        try:
            self.sock.connect(server_address)
        except Exception as e:
            print("Error : Could not connect to socket")
            exit(1)

        self.check(self.sinput(), 220) # receive and check greeting message from the server
        self.sprint(f"HELO {host}") # respond to the server's greeting message
        self.check(self.sinput(), 250) # receive and check the server's response for the sent greeting message.
        self.sprint(f"MAIL FROM: <{self.email_from.getter()}>") # sent MAIL FROM command
        self.check(self.sinput(), 250) # receive and check server's response
        for rcpt in self.email_rcpt:
            self.sprint(f"RCPT TO: <{rcpt.getter()}>") # send RCPT TO command
            self.check(self.sinput(), 250) # receive and check server's response for RCPT TO command
        self.sprint("DATA") # send DATA command
        self.check(self.sinput(), 354) # receive and check server's response for DATA command
        for line in self.data:
            self.sprint(line) # send saved email message to the server.
        self.sprint(".") # send saved '.' to the server indicating the end of DATA.
        self.check(self.sinput(), 250) # receive and check server's response for '.' command
        self.sprint("QUIT") # send QUIT command
        self.check(self.sinput(), 221) # receive and check server's response for QUIT command and terminate the client agent

    # check whether server response is correct.
    def check(self, line, code):
        if line.split()[0] != str(code):
            print(f"Server Error: {line}")
            self.sock.close()
            exit(1)

    # Send data through the socket connection.
    def sprint(self, line, end="\n"):
        line += end
        self.sock.sendall(line.encode("utf-8"))

    # Recieve data from the socket connection.
    def sinput(self):
        return self.sock.recv(self.DATASIZE).decode("utf-8")

    def null_space(self, least=0):
        if least != 0:
            if self.scanner.peek() != " " and self.scanner.peek() != "\t":
                self.echo_error(500)
                return
            self.scanner.read()
        while True:
            if self.scanner.peek() != " " and self.scanner.peek() != "\t":
                break
            else:
                self.scanner.read()

"""
    Scanner class helps to peek and read the data from the client interface.
"""
class Scanner:
    def __init__(self, stdread):
        self.stdread = stdread
        self.tracker = 0

    def peek(self, length=1):
        return self.stdread[self.tracker:self.tracker + length]

    def read(self, length=1):
        word = self.peek(length)
        self.tracker += length
        return word

    def line(self):
        return self.stdread

    def reach_end(self, length=1):
        if len(self.stdread) < self.tracker + length:
            return True
        else:
            return False


class MailboxNode:
    def __init__(self, local_part, domain):
        self.local_part = local_part
        self.domain = domain

    def getter(self):
        return self.local_part + "@" + self.domain

    def domain_getter(self):
        return self.domain


class Mailbox:
    def __init__(self, state, scanner):
        self.state = state
        self.scanner = scanner

    def echo_error(self):
        self.state = "ERROR"

    def null_space(self):
        while True:
            if self.scanner.peek() != " " and self.scanner.peek() != "\t":
                break
            else:
                self.scanner.read()

    def email(self):
        self.null_space()
        email = self.mailbox()
        if self.state == "ERROR":
            return
        self.null_space()
        if not self.scanner.reach_end():
            self.echo_error()
        return email

    def mailbox(self):
        local_part = self.local_part()
        if self.state == "ERROR":
            return
        if self.scanner.read() != "@":
            self.echo_error()
        domain = self.domain()
        if self.state == "ERROR":
            return
        return MailboxNode(local_part, domain)

    def local_part(self):
        local_part = []
        special = ['<', '>', '(', ')', '[', ']', '\\', '.', ',', ';', '@', '"'] + [' ', '\t', '']
        while True:
            if self.scanner.peek() not in special:
                local_part.append(self.scanner.read())
            else:
                if len(local_part) == 0 or self.scanner.peek() != "@":
                    self.echo_error()
                return "".join(local_part)

    def domain(self):
        domain = []
        while True:
            element = self.element()
            if self.state == "ERROR":
                return
            domain.append(element)
            if self.scanner.peek() == '.':
                self.scanner.read()
                domain.append(".")
            else:
                return "".join(domain)

    def element(self):
        element = []
        if not self.scanner.peek().isalpha():
            self.echo_error()
            return
        while True:
            if self.scanner.peek().isalpha() or self.scanner.peek().isdigit():
                element.append(self.scanner.read())
            else:
                return "".join(element)


def safe_input(prompt=""):
    a = ""
    try:
        a = input(prompt)
    except EOFError:
        exit(1)
    return a


if __name__ == '__main__':
    client = interface()
    client.main()