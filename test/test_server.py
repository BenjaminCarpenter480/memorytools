import http.server
import socketserver
import sys
import time
import numpy as np

import psutil

PORT = 8130


class MyHandler(http.server.BaseHTTPRequestHandler):
    data_array = []
    
    def __init__(self, request, client_address, server) -> None:
        super().__init__(request, client_address, server)
        socketserver.TCPServer.allow_reuse_address = True
        
        
    def do_GET(self):
        if self.path == "/addmem":
            # Handle the command here
            print(len(MyHandler.data_array))
            MyHandler.data_array.append(list(np.random.default_rng().bytes(int(1e6)))) #Add a MB of memory
            print("Added memory")
            print(psutil.Process().memory_info().vms)
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Command received")

        elif self.path == "/clrmem":
            # Handle the command here
            del MyHandler.data_array
            MyHandler.data_array = [] #Reset the data array
            print("remove memory")
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Command received")

        elif self.path == "/test":
            # # Handle the command here
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Command received")
            
        elif self.path == "/exit":
            self.send_response(200)
            self.send_header("Content-type", "text/plain") 
            self.end_headers()
            self.wfile.write(b"Command received")
            self.connection.close()
            time.sleep(1)
            global exit_server
            httpd.server_close()  # Release the port in use
            exit_server = True
            # httpd.finish_request(self.request, self.client_address)
            # self.finish()

        else:
            self.send_error(404)

if __name__ == "__main__":
    
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at port {PORT}")
        global exit_server
        exit_server = False
        while not exit_server:
            httpd.handle_request()
        httpd.socket.close()
        httpd.server_close()
        print("SERVER CLOSED")
        sys.exit(0)