import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Secrets:
    DEFAULTS = {
        "db_con": "mysql.example.com:3306",
        "db_user": "demoUser",
        "db_password": "demoPassword",
    }

    def __init__(self):
        self.config_location = ""
        self.db_con = ""
        self.db_user = ""
        self.db_password = ""
        self._lock = threading.Lock()

    def read_current_configuration(self):
        config_paths = ["./credentials", "/secrets/credentials"]
        for path in config_paths:
            if os.path.isfile(path):
                self.config_location = path
                break
        else:
            raise RuntimeError("fatal error config file: credentials not found")

        self.reload_settings()
        self._start_watcher()

    def reload_settings(self):
        values = dict(self.DEFAULTS)
        with open(self.config_location) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    values[key.strip()] = val.strip().strip('"')

        with self._lock:
            self.db_con = values["db_con"]
            self.db_user = values["db_user"]
            self.db_password = values["db_password"]

        print(f"Reading configuration from {self.config_location}")
        print(f"Connection string is {self.db_con}")
        print(f"Username is {self.db_user}")
        print(f"Password is {self.db_password}")

    def _start_watcher(self):
        handler = _ConfigChangeHandler(self)
        observer = Observer()
        observer.schedule(handler, os.path.dirname(self.config_location) or ".", recursive=False)
        observer.daemon = True
        observer.start()


class _ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, secrets):
        self.secrets = secrets

    def on_modified(self, event):
        if event.src_path.endswith("credentials"):
            print(f"Config file changed: {event.src_path}")
            self.secrets.reload_settings()


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, secrets, *args, **kwargs):
        self.secrets = secrets
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/health/live":
            self._respond(200, "text/plain", "up\n")
        elif self.path == "/health/ready":
            self._respond(200, "text/plain", "yes\n")
        else:
            with self.secrets._lock:
                body = (
                    "<body>"
                    "<h1>I am a Python application running inside Kubernetes.</h1>"
                    "<h2>My properties are:</h2>"
                    f"<p>I read my secrets from {self.secrets.config_location}</p>"
                    "<h2> Database connection details</h2>"
                    f"<ul><li>{self.secrets.db_con}</li>"
                    f"<li>{self.secrets.db_user}</li>"
                    f"<li>{self.secrets.db_password}</li>"
                    "</ul></body>"
                )
            self._respond(200, "text/html; charset=utf-8", body)

    def _respond(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        # Use default logging
        super().log_message(format, *args)


def main():
    port = int(os.environ.get("PORT", "8080"))

    secrets = Secrets()
    secrets.read_current_configuration()

    def handler(*args, **kwargs):
        RequestHandler(secrets, *args, **kwargs)

    server = HTTPServer(("", port), handler)
    print(f"Simple web server is listening now at port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
