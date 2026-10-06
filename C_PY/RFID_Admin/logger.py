import logging
import os
import sys

app_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(app_path, "app.log")

logging.basicConfig(
    filename=log_file,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
)

def log_error(msg):
    logging.error(msg)
    print(msg)
