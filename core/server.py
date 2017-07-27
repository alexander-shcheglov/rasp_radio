# coding: utf-8

import pickle
import socket
import queue
import select

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP
WRITE_ONLY = select.POLLOUT | select.POLLERR | select.POLLHUP
READ_WRITE = select.POLLOUT | READ_ONLY
WITH_ERRORS = select.POLLERR | select.POLLHUP
POLL_TIMEOUT = 0.1


class CommandServer(object):

    def __init__(self, server_address):
        self.socket_pool = {}
        self.command_pool = queue.Queue()
        self.notification_pool = {}
        self.last_notification = None
        self._interrupted = False
        self.socket = None
        self.open_socket(server_address)
        self.poller = select.poll()
        self.poller.register(self.socket, READ_ONLY)

    def open_socket(self, server_address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.socket.bind(server_address)
        self.socket.listen()
        self.socket_pool.update({self.socket.fileno(): self.socket})

    def server_close(self):
        """
        close all sockets
        :return: None
        """
        for file_d in list(self.socket_pool.keys()):
            self.close_connection(file_d)

    def close_connection(self, file_d, sock=None):
        """
        close socket, remove from socket pool,
        remove notification queue for socket
        :param file_d: file descriptor
        :param sock: socket
        :return: None
        """
        self.poller.unregister(file_d)
        sock = sock or self.get_socket(file_d)
        sock.close()
        try:
            del self.socket_pool[file_d]
            del self.notification_pool[file_d]
        except KeyError:
            pass

    def new_connection(self):
        """
        get new socket and
        put last notification to socket notification queue
        :return: None
        """
        try:
            sock, address = self.socket.accept()
            sock.setblocking(False)
            fd = sock.fileno()
            self.socket_pool.update({fd: sock})
            self.poller.register(sock, READ_WRITE)
            self.notification_pool[fd] = queue.Queue()
            if self.last_notification:
                self.notification_pool[fd].put(self.last_notification)
        except OSError:
            pass

    def get_socket(self, fd):
        return self.socket_pool[fd]

    def read_command(self, fd, sock):
        """
        read command from socket, save in command queue
        :param fd: file descriptor
        :param sock: socket
        :return: None
        """
        if sock == self.socket:
            self.new_connection()
        else:
            data = sock.recv(1024)
            if data:
                self.command_pool.put(pickle.loads(data))

    def send_notification(self, fd, sock):
        """
        send notification to socket
        :param fd: file descriptor
        :param sock: socket
        :return: None
        """
        try:
            if not self.notification_pool[fd].empty():
                sock.sendall(pickle.dumps(self.notification_pool[fd].get()))
        except OSError:
            self.close_connection(fd, sock)

    def poll_run(self):
        """
        work with socket poll: read, write, remove with errors
        :return: None
        """
        for fd, event in self.poller.poll(POLL_TIMEOUT):
            sock = self.get_socket(fd)
            # read commands or new connections
            if event & (select.POLLIN | select.POLLPRI):
                self.read_command(fd, sock)
            # send notifications to sockets
            elif event & select.POLLOUT and sock != self.socket:
                self.send_notification(fd, sock)
            # remove sockets with errors
            elif event & WITH_ERRORS and sock != self.socket:
                self.close_connection(fd, sock)

    def process_command_pool(self):
        """
        process command queue
        :return: None
        """
        while not self.command_pool.empty():
            command = self.command_pool.get()
            notification = self.process_command(command)
            if notification:
                self.notify(notification)

    def process_command(self, command):
        """
        dispatcher for command
        :param command: (Command_type, method, **kwargs)
        :return: Notification(maybe)
        """
        raise NotImplementedError

    def loop(self):
        """
        main loop: read commands, write notifications, remove socket with errors
        :return: None
        """
        try:
            while not self._interrupted:
                self.poll_run()
                self.process_command_pool()
        except (KeyboardInterrupt, OSError) as e:
            pass
        self.server_close()

    def notify(self, notification):
        """
        we must put new notification in queue for every socket
        :param notification: (Message_type, message, stats={})
        :return: None
        """
        self.last_notification = notification
        for v in self.notification_pool.values():
            v.put(notification)
