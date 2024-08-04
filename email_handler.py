import imaplib
import email
from email.header import decode_header
import os
import re
import process_files
import database

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename).replace('\r', '').replace('\n', '')

def process_emails(server, port, username, password, keywords, fetch_all=False):
    # Conectar ao servidor IMAP com SSL
    imap = imaplib.IMAP4_SSL(server, port)
    imap.login(username, password)

    # Selecionar a caixa de entrada
    imap.select("inbox")

    # Buscar emails não lidos ou todos os emails
    status, messages = imap.search(None, 'ALL' if fetch_all else 'UNSEEN')
    email_ids = messages[0].split()

    for email_id in email_ids:
        # Buscar o email pelo ID
        status, msg_data = imap.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Parsear o email
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")

                from_ = msg.get("From")
                print("Subject:", subject)
                print("From:", from_)

                # Se o email tiver anexos
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_maintype() == "multipart":
                            continue
                        if part.get("Content-Disposition") is None:
                            continue

                        filename = part.get_filename()
                        if filename:
                            filename = sanitize_filename(filename)
                            print(f"Found attachment: {filename}")
                            if filename.endswith('.pdf') or filename.endswith('.docx'):
                                if not os.path.isdir("downloads"):
                                    os.mkdir("downloads")
                                filepath = os.path.join("downloads", filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                print(f"Downloaded {filename}")
                                # Salvar no banco de dados
                                process_files.process_file(filepath, keywords)
                                database.save_resume(subject, filepath, from_, "", "email")

    # Fechar a conexão e logout
    imap.close()
    imap.logout()

def process_unseen_emails(keywords):
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    process_emails("mail.rhf.com.br", 993, username, password, keywords, fetch_all=False)

def process_all_emails(keywords):
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    process_emails("mail.rhf.com.br", 993, username, password, keywords, fetch_all=True)
