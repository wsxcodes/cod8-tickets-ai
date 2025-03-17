import smtplib
from email.mime.text import MIMEText

def send_email():
    smtp_host = 'smtp.office365.com'
    smtp_port = 587
    username = 'support@cod8.io'
    password = 'tgmqyzfgdxszncff'

    from_addr = username
    to_addr = 'jakub.kudlacek@cod8.io'
    subject = 'Test Email'
    body = 'helloWorld("print")'

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    # Connect, log in, send
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()  # Remove if using port 465 + SMTP_SSL
        server.login(username, password)
        server.send_message(msg)

if __name__ == '__main__':
    send_email()
