import logging
import smtplib
from email.mime.text import MIMEText

from semantic_kernel.utils.logging import setup_logging

from backend import config

# Set up logging for the kernel
setup_logging()

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

    logging.info("Attempting to send email from %s to %s with subject '%s'", from_addr, to_addr, subject)

    # Connect, log in, send
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()  # Remove if using port 465 + SMTP_SSL
        server.login(username, password)
        server.send_message(msg)

    logging.info("Email successfully sent to %s", to_addr)
