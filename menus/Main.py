from helpers import WinduSocketServer
from helpers import KThread
from pydispatch import dispatcher
import Client
import threading
import os, sys, time, cmd
import argparse
import base64
import gevent
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketServer
import geventwebsocket

class Leviathan:
	#This is the only way I could think of having clients available across classes. Probably not a good practice
	sessions = {}
	def __init__(self, BindIP, port, certfile=None):
		self.host = BindIP 
		self.port = port
		self.clientName = ""
		self.clientUser = ""
		self.sessionName = ""
		self.certfile = certfile
		self.lock = threading.Lock()

	def startServer(self):
		"""Starts the server"""

		if not self.certfile:
			server = WebSocketServer((self.host, self.port), self.handleClient)
		else:
			server = WebSocketServer((self.host, self.port), self.handleClient, self.certfile)

		server.serve_forever()

	def default_response():
		page = "<html><body><h1>It works!</h1>"
		page += "<p>This is the default web page for this server.</p>"
		page += "<p>The web server software is running but no content has been added, yet.</p>"
		page += "</body></html>"
		return page

	def handleHTTP(self, environ, start_response):
		start_response("200 OK", [("Content-Type", "text/html")])
		return [self.default_response()]

	def handleClient(self, environ, start_response):
		
		if environ["PATH_INFO"] == "/connect":
			if environ["wsgi.websocket"] != None:
				
				ws = environ["wsgi.websocket"]
				addr = environ["REMOTE_ADDR"]
				clientMsg = ws.receive()
				#client will always send the hostname, current user with the first message
				print "Received Upgrade request, waiting for client info...\n"
				clientName, clientUser = clientMsg.encode('ascii').split('|')
				self.clientName = clientName
				self.clientUser = clientUser
				self.sessionName = "%s@%s" % (self.clientUser, self.clientName)
				#Jump to the client menu
				clientMenu = Client.Leviathan(ws, self.clientName, self.clientUser)
				clientMenu.cmdloop()
				#Not sure about what to return to the application
				return environ
			else:
				return self.handleHTTP(environ, start_response)

		else:
			return self.handleHTTP(environ, start_response)