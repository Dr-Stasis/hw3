from socket import*
import os
import sys

crlf = ord('\n')  # = 10

special = ['<', '>', '(', ')', '\\', '.', ',', ';', ':', '@', '"']

commands = ["HELO", "MAIL FROM:", "RCPT TO:", "DATA", "QUIT"]

valid_responses = {
    "MAIL FROM:": "250 OK",
    "RCPT TO:": "250 OK",
    "DATA": "354 Start mail input; end with . on a line by itself"
}


def read_commands():

    # Initialize MAIL FROM and RCPT TO commands
    rcpt_to_cmd = ""

    # Initialize result and expected command
    result, expected_command = "", "MAIL FROM:"

    # Initialize socket
    port_number = int(sys.argv[1])
    print(port_number)
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind(('', port_number))
    hostname = gethostname
    server_socket.listen(1)
    connection_socket, addr = server_socket.accept()
    connection_socket.send(f"220 {hostname}".encode())
    print(f"220 {hostname}")

    while True:
        command = connection_socket.recv(256).decode()

        if not command:
            # Send response to client
            connection_socket.send(f"Server encountered non-protocol error".encode())
            # Echo response
            print(f"Server encountered non-protocol error")
            return

        # Echo line received command from client
        sys.stdout.write(command)

        # Split command into tokens, delimited by <nullspace> characters and <CRLF>
        # <nullspace> ::= no character | space or tab
        # <CRLF> ::= newline character
        tokens = command.split()

        # Initialize command name
        command_name = "UNKNOWN"

        # Try to assign command name from command
        # Make sure at least one token exist in command
        if len(tokens) > 0:
            # Check if first token consist of command
            if tokens[0][:4] in commands:
                command_name = tokens[0][:4]
            # Make sure at least two tokens exist in command
            elif len(tokens) > 1:
                # Check if first and second token consist of "MAIL FROM:"
                if tokens[0][:4] == "MAIL" and tokens[1][:5] == "FROM:":
                    command_name = "MAIL FROM:"
                elif tokens[0][:4] == "RCPT" and tokens[1][:3] == "TO:":
                    command_name = "RCPT TO:"

        # Check if command is a valid command
        if command_name in commands and not command[0].isspace():
            # Command is expected
            if command_name == expected_command:
                # Parse the remainder of the command
                if command_name == "HELO":
                    result, expected_command = parse_helo(tokens)
                elif command_name == "MAIL FROM:":
                    result, expected_command = parse_mail_from(tokens)
                elif command_name == "RCPT TO:":
                    result, expected_command = parse_rcpt_to(tokens)
                elif command_name == "DATA":
                    result, expected_command = parse_data(tokens)
                elif command_name == "QUIT":
                    result, expected_command = parse_quit(tokens)

                # Output error message
                if result != "ok":
                    sys.stdout.write(result)
                # Make sure the last character is a <CRLF>
                else:
                    # The command is valid
                    if ord(command[-1]) == crlf:

                        valid_response = ""
                        if command_name in valid_responses:
                            valid_response = valid_responses[command_name]
                        elif command_name == "HELO":
                            valid_response = f"250 Hello {tokens[1]} pleased to meet you"
                        elif command_name == "QUIT":
                            valid_response = f"221 {hostname} closing connection"

                        # Send the valid response
                        connection_socket.send(valid_response.encode())
                        # Echo the valid response
                        print(valid_response)

                        if command_name == "RCPT TO:":
                            # Store the recipient command line for later reference
                            rcpt_to_cmd = command
                        elif command_name == "DATA":
                            # Read received data from client
                            response = read_data(rcpt_to_cmd, connection_socket)
                            # Send response to client
                            connection_socket.send(response.encode())
                            # Echo response
                            print(response)
                            if response != "250 OK":
                                # Close socket connected to client
                                connection_socket.close()
                                # Re-initialize this server
                                return
                        elif command_name == "QUIT":
                            # Close socket connected to client
                            connection_socket.close()
                            # Re-initialize this server
                            return

                    # The command does not end in <CRLF>
                    else:
                        # Output "501 Syntax error in parameters or arguments" message
                        connection_socket.send("501 Syntax error in parameters or arguments".encode())
                        print("501 Syntax error in parameters or arguments")
                        # Reset expected command
                        expected_command = command_name
            # Command is not expected
            else:
                # Output "503 Bad sequence of commands" message
                connection_socket.send("503 Bad sequence of commands")
                print("503 Bad sequence of commands")
        # Command is not a valid command, output
        else:
            # Output "500 Syntax error: command unrecognized" message
            connection_socket.send("500 Syntax error: command unrecognized")
            print("500 Syntax error: command unrecognized")


# A command will consist of either 1, 2 or 3 tokens after being split, depending on the command name
# ex. DATA\r and DATA \n amount to 1 token
# ex. MAIL FROM:<reverse-path>\n and MAIL FROM:<reverse-path> \n amount to 2 tokens
# ex. RCPT TO: <reverse-path>\n and RCPT TO: <forward-path> \n amount to 3 tokens

def parse_helo(tokens):

    err = "501 Syntax error in parameters or arguments", "HELO"

    if tokens[0] != "HELO":
        return "500 Syntax error: command unrecognized", "HELO"

    if len(tokens) != 2:
        return err

    # <helo-cmd> ::= "HELO" <whitespace> <domain> <nullspace> <CRLF>
    # <nullspace> & <CRLF> eliminated during command.split(); therefore only HELO and domain should remain

    domain = tokens[1]

    # Split <domain> by "." delimiter
    elements = domain.split('.')

    # Either duplicate "." was found, or one was found at either the beginning or the end
    if '' in elements:
        return err

    # Verify elements of <domain>
    for element in elements:
        # Verify that first character in <element> is a <letter>
        if not element[0].isalpha():
            return err
        # Verify that all characters in <element> are in <let-dig-hyphen>
        for char in element:
            if (not char.isalnum()) and ord(char) != ord('-'):
                return err

    return "ok", "MAIL FROM:"


def parse_mail_from(tokens):
    return parse_path("MAIL FROM:", tokens)


def parse_rcpt_to(tokens):
    return parse_path("RCPT TO:", tokens)


def parse_path(command_name, tokens):
    # The command name was recognized; all possible remaining errors are syntax errors
    err = "501 Syntax error in parameters or arguments", command_name

    # Verify that # of tokens is valid
    if len(tokens) != 2 | len(tokens) != 3:
        return err

    # Determine size of second string in command name
    second_string_len = len(command_name.split()[1])

    # Define <path>
    path = tokens[1][second_string_len:] if len(tokens) == 2 else tokens[2]

    # Verify that the first character of <path> is '<'
    if ord(path[0]) != ord('<'):
        return err

    # Verify that the last character of <path> is '>'
    if ord(path[-1]) != ord('>'):
        return err

    # <path> ::= "<" <mailbox> ">"
    # <mailbox> ::= <local-part> "@" <domain>
    # <local-part> ::= <char> | <char> <string>
    # <char> ::= all ASCII characters, excluding <special> and <SP>
    # <domain> ::= <element> | <element> "." <domain>
    # <element> ::= <letter> | <name>
    # <name> ::= <letter> <let-dig-hyphen-str>
    # <let-dig-hyphen-str> ::= <let-dig-hyphen> | <let-dig-hyphen> <let-dig-hyphen-str>
    # <let-dig-hyphen> ::= <letter> | <digit> | "-"

    # Define <mailbox> by removing angle brackets from <path> and splitting via delimiter "@"
    mailbox = path[1:-1].split('@')

    # Verify that there is exactly one "@" in <mailbox>
    if len(mailbox) != 2:
        return err

    # Define <local-path> and <domain>
    local_path, domain = mailbox[0], mailbox[1]

    # Verify <local-path>
    for char in local_path:
        if char in special or char.isspace():
            return err

    # Split <domain> by "." delimiter
    elements = domain.split('.')

    # Either duplicate "." was found, or one was found at either the beginning or the end
    if '' in elements:
        return err

    # Verify elements of <domain>
    for element in elements:
        # Verify that first character in <element> is a <letter>
        if not element[0].isalpha():
            return err
        # Verify that all characters in <element> are in <let-dig-hyphen>
        for char in element:
            if (not char.isalnum()) and ord(char) != ord('-'):
                return err

    # <path> is verified
    return "ok", ("RCPT TO:" if command_name == "MAIL FROM:" else "DATA")


def parse_data(tokens):

    # ex. DATAX
    if tokens[0] != "DATA":
        return "500 Syntax error: command unrecognized", "DATA"

    if len(tokens) != 1:
        return "501 Syntax error in parameters or arguments", "DATA"

    return "ok", "QUIT"


def read_data(rcpt_to_cmd, connection_socket):

    rcpt_tokens = rcpt_to_cmd.split()
    rcpt_path = rcpt_tokens[1][3:] if len(rcpt_tokens) == 2 else rcpt_tokens[2]
    rcpt_path = rcpt_path.strip('<').strip('>')
    rcpt_path = rcpt_path.split('@')[1]
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    file = open(os.path.join(__location__, 'forward/'+rcpt_path), 'a')

    while True:
        data = connection_socket.recv(256).decode()
        # Echo the received input
        print(data)

        # Append data to file
        file.write(data)

        # The connection socket was closed prematurely
        if not data:
            return "Server encountered non-protocol error"

        if data == "\n.\n":
            # Close file
            file.close()
            return "250 OK"


def parse_quit(tokens):

    # ex. QUITX
    if tokens[0] != "QUIT":
        return "500 Syntax error: command unrecognized", "QUIT"

    if len(tokens) != 1:
        return "501 Syntax error in parameters or arguments", "QUIT"

    return "ok", "MAIL FROM:"


read_commands()
