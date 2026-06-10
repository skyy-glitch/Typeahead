import json
import os
import sys
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

# Ensure the files directory is in the path so we can import modules
api_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(api_dir, '..'))
files_dir = os.path.join(root_dir, 'files')
if files_dir not in sys.path:
    sys.path.append(files_dir)

from typeahead import TypeaheadEngine

# Initialize the typeahead engine with limit of 8 by default
# This will be cached across warm invocations of the serverless function
engine = TypeaheadEngine(limit=8)

class handler(BaseHTTPRequestHandler):
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
            self.send_json(404, {"error": "Endpoint not found"})

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
