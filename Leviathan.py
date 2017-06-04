#!/usr/bin/python2.7
#author: @xorrior (Chris Ross)

import os, cmd, sys, datetime, time
from menus import Main
import argparse
import base64


def main():
	parser = argparse.ArgumentParser(description="Start a Leviathan Server")
	parser.add_argument('--endpoint', help="Specific IP to bind the listener", required=True)
	parser.add_argument('--port', type=int, help="Port to use", required=True)
	parser.add_argument('--certfile', help="path to the cert file to use for SSL. Optional.")

	args = parser.parse_args()

	host = args.endpoint
	port = args.port

	if not args.certfile:
		server = Main.Leviathan(host, port)
	else:
		server = Main.Leviathan(host, port, certfile=args.certfile)

	try:
		print "Listening for connection....\n"
		server.startServer()
	except KeyboardInterrupt:
		exit = raw_input("Shutdown Leviathan Listener (Y/N) ??")
		if exit.lower() == "y":
			sys.exit(0)
		else:
			pass

if __name__ == "__main__":
	main()
							
