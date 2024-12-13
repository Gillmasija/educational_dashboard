import os
import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        raise

if __name__ == "__main__":
    main()
