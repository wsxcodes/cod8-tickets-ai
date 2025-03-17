import smtplib
from email.mime.text import MIMEText
from backend import config

def send_email(to_addr: str, subject: str, body: str):
    smtp_host = config.SMTP_SERVER
    smtp_port = config.SMTP_PORT
    username = config.SMTP_USERNAME
    password = config.SMTP_PASSWORD

    from_addr = username
 
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    # Connect, log in, send
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()  # Remove if using port 465 + SMTP_SSL
        server.login(username, password)
        server.send_message(msg)
