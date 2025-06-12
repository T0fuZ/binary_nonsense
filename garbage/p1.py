
import time
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import paramiko

watched_files = [
    {
        "local": "/path/to/file1.txt",
        "remote": "/remote/path1/file1.txt"
    },
    {
        "local": "/path/to/file2.conf",
        "remote": "/remote/path2/file2.conf"
    }
]

remote_host = "your.server.com"
remote_port = 22
remote_user = "username"
remote_pass = "password"

# Coalescing timers for each file
debounce_timers = {}
debounce_delay = 1.5  # seconds

def send_file_to_server(local_path, remote_path):
    print(f"Sending {local_path} -> {remote_path}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, port=remote_port, username=remote_user, password=remote_pass)
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        ssh.close()
        print("Transfer complete.")
    except Exception as e:
        print(f"Upload failed: {e}")

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            abs_path = os.path.abspath(event.src_path)
            for entry in watched_files:
                local_path = os.path.abspath(entry["local"])
                if abs_path == local_path:
                    # Cancel previous timer if running
                    if local_path in debounce_timers:
                        debounce_timers[local_path].cancel()

                    # Start new timer
                    timer = threading.Timer(debounce_delay, send_file_to_server, args=(local_path, entry["remote"]))
                    debounce_timers[local_path] = timer
                    timer.start()

if __name__ == "__main__":
    watch_dirs = list(set(os.path.dirname(entry["local"]) for entry in watched_files))
    observer = Observer()
    handler = FileChangeHandler()

    for path in watch_dirs:
        observer.schedule(handler, path, recursive=False)

    observer.start()
    print("Watching for changes with coalesced debounce...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
