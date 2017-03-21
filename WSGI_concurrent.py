# coding:utf-8
import socket
import StringIO
import sys
import errno
import signal
import os
# import time


class WSGIServer(object):
    address_family = socket.AF_INET  # 服务器之间网络通信，IP V4
    socket_type = socket.SOCK_STREAM  # 流式socket , for TCP
    request_queue_size = 1  # 开始监听TCP传入连接。backlog指定在拒绝连接之前，操作系统可以挂起的最大连接数量。该值至少为1，大部分应用程序设为5就可以了

    def __init__(self, server_address):
        self.listen_socket = listen_socket = socket.socket(self.address_family, self.socket_type)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow to reuse the same address
        listen_socket.bind(server_address)
        listen_socket.listen(self.request_queue_size)
        host, port = self.listen_socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        self.headers_set = []

    def set_app(self, application):
        self.application = application

    def server_forever(self):
        listen_socket = self.listen_socket
        signal.signal(signal.SIGCHLD, self.grim_reaper)  # 异步处理fork的子进程exit时未被父进程处理其status产生的僵尸进程（zombies）
        while True:
            try:
                self.client_connection, client_address = listen_socket.accept()
            except IOError as e:
                code, msg = e.args
                # restart accept if it was interrupted
                if code == errno.EINTR:
                    continue
                else:
                    raise
            pid = os.fork()
            if pid == 0:  # child
                self.listen_socket.close()  # close child copy
                self.handle_one_request()
                self.client_connection.close()
                os._exit(0)
            else:
                self.client_connection.close()

    def handle_one_request(self):
        self.request_data = request_data = self.client_connection.recv(1024)
        print ''.join('< {line}\n'.format(line=line) for line in request_data.splitlines())

        self.parse_request(request_data)
        env = self.get_environ()
        result = self.application(env, self.start_response)
        self.finish_response(result)
        # time.sleep(20)
    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')
        self.request_method, self.path, self.request_version = request_line.split()

    def get_environ(self):
        env = {}
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = StringIO.StringIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        # Required CGI variables
        env['REQUEST_METHOD'] = self.request_method  # GET
        env['PATH_INFO'] = self.path  # /hello
        env['SERVER_NAME'] = self.server_name  # localhost
        env['SERVER_PORT'] = str(self.server_port)  # 8889
        return env

    def start_response(self, status, response_headers, exc_info = None):
        server_headers = [('Date', 'Tue,  20 Mar 2017 15:56:48 GMT'),
                          ('Server', 'WSGIServer 0.2')]
        self.headers_set = [status, response_headers + server_headers]

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            for data in result:
                response += data
            print ''.join('> {line}\n'.format(line=line) for line in response.splitlines())
            self.client_connection.sendall(response)
        finally:
            self.client_connection.close()

    def grim_reaper(self, signum, frame):
        """处理高并发下僵尸进程的处理"""
        while True:
            try:
                pid, status = os.waitpid(
                    -1,   # Wait for any child process
                    os.WNOHANG)    # Do not block and return EWOULDBLOCK error
            except OSError:
                return

            if pid ==0:
                return


SERVER_ADDRESS = (HOST, PORT) = '', 8889


def make_server(server_address, application):
    server = WSGIServer(server_address)
    server.set_app(application)
    return server

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('provide a WSGI application object as modele:callable')
    app_path = sys.argv[1]
    module, application = app_path.split(':')
    module = __import__(module)
    application = getattr(module, application)
    httpd = make_server(SERVER_ADDRESS, application)
    print 'WSGIServer: Server HTTP on port {port} ...\n'.format(port=PORT)
    httpd.server_forever()

