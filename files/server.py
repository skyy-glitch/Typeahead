import json
import os
import sys
import time
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure the script directory is in the path so we can import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from typeahead import TypeaheadEngine

# Initialize the typeahead engine with limit of 8 by default
engine = TypeaheadEngine(limit=8)

class TypeaheadHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging to server output instead of clogging stdout
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/api/suggest':
            query_params = parse_qs(parsed_path.query)
            q = query_params.get('q', [''])[0]
            limit_str = query_params.get('limit', ['8'])[0]
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 8
            
            results = engine.suggest(q, limit=limit)
            self.send_json(200, results)

        elif path == '/api/stats':
            self.send_json(200, engine.stats())

        else:
            # Serve static files from ../frontend/
            self.serve_static_file(path)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''

        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})
            return

        if path == '/api/add':
            city = data.get('city', '').strip()
            state = data.get('state', '').strip()
            if not city:
                self.send_json(400, {"error": "City name is required"})
                return
            
            # Capitalize properly
            city = city.title()
            state = state.title()
            engine.add(city, state or "Unknown")
            self.send_json(200, {"success": True, "message": f"Added city '{city}' ({state})"})

        elif path == '/api/remove':
            city = data.get('city', '').strip()
            if not city:
                self.send_json(400, {"error": "City name is required"})
                return
            
            existed = engine.remove(city)
            if existed:
                self.send_json(200, {"success": True, "message": f"Removed city '{city}'"})
            else:
                self.send_json(200, {"success": False, "message": f"City '{city}' not found"})

        elif path == '/api/select':
            city = data.get('city', '').strip()
            state = data.get('state', '').strip()
            if not city:
                self.send_json(400, {"error": "City name is required"})
                return
            engine.record_click(city, state)
            self.send_json(200, {"success": True, "message": f"Recorded search selection for '{city}'"})

        else:
            self.send_json(404, {"error": "Endpoint not found"})

    def serve_static_file(self, path):
        # Default route to index.html
        if path == '/' or path == '':
            path = '/index.html'

        # Relative path from files/ to frontend/
        frontend_dir = os.path.abspath(os.path.join(script_dir, '..', 'frontend'))
        
        # Remove leading slash and construct local path
        local_path = os.path.abspath(os.path.join(frontend_dir, path.lstrip('/')))
        
        # Security check: ensure file is inside frontend directory
        if not local_path.startswith(frontend_dir):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if not os.path.exists(local_path) or os.path.isdir(local_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        # Determine MIME type
        _, ext = os.path.splitext(local_path)
        mime_types = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon'
        }
        content_type = mime_types.get(ext.lower(), 'application/octet-stream')

        try:
            with open(local_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Internal Server Error: {str(e)}".encode('utf-8'))

def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, TypeaheadHTTPRequestHandler)
    print(f"Typeahead API and web server started at http://localhost:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
