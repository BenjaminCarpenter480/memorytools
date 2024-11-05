import http.server
import socketserver
import sys
import time
import numpy as np
import psutil
import logging

PORT = 8130


class TestHandler(http.server.BaseHTTPRequestHandler):
    data_array = []
    
    def __init__(self, request, client_address, server) -> None:
        super().__init__(request, client_address, server)
        logging.basicConfig(level=logging.INFO)
        
    def do_GET(self):
        try:
            if self.path == "/addmem":
                # Handle the command here
                logging.info(f"Current data array length: {len(TestHandler.data_array)}")
                TestHandler.data_array.append(list(np.random.default_rng().bytes(int(1e6)))) # Add a MB of memory
                logging.info("Added memory")
                logging.info(f"Current VMS: {psutil.Process().memory_info().vms}")
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Command received")

            elif self.path == "/clrmem":
                # Handle the command here
                del TestHandler.data_array
                TestHandler.data_array = [] # Reset the data array
                logging.info("Cleared memory")
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Command received")

            elif self.path == "/test":
                # Handle the command here
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Command received")
                
            elif self.path == "/exit":
                self.send_response(200)
                self.send_header("Content-type", "text/plain") 
                self.end_headers()
                self.wfile.write(b"Command received")
                self.server.shutdown()  # Properly shutdown the server
                self.server.server_close()  # Release the port in use

            else:
                self.send_error(404)
        except Exception as e:
            logging.error(f"Error handling request: {e}")
            self.send_error(500, f"Server error: {e}")

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True  # Allow reuse of the address
    with socketserver.TCPServer(("", PORT), TestHandler) as httpd:
        logging.info(f"Serving at port {PORT}")
        global exit_server
        exit_server = False
        while not exit_server:
            httpd.handle_request()
        httpd.socket.close()
        httpd.server_close()
        logging.info("SERVER CLOSED")
        sys.exit(0)