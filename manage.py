from django.core.management import execute_from_command_line
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    
    # Start up OpenTelemetry for Django in Development
    # Only when running the server
    if len(sys.argv) > 1 and sys.argv[1] in ("runserver", "runsslserver"):
        from config.otel import setup_opentelemetry
        setup_opentelemetry()

    execute_from_command_line(sys.argv)
