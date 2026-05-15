import http.server
import socketserver
import os

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Tell the handler to serve files from the 'dist' subdirectory
        super().__init__(*args, directory="dist", **kwargs)

    def do_GET(self):
        # Fix the path check to look inside the 'dist' folder
        # self.translate_path returns the path relative to the 'directory' arg above
        requested_path = self.translate_path(self.path)

        if not os.path.exists(requested_path):
            self.path = 'index.html'

        return super().do_GET()

PORT = 3000

# Allow address reuse so restarts don't hang on "Address already in use"
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving Auuki from ./dist at port {PORT}")
    httpd.serve_forever()