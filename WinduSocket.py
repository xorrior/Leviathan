#!/usr/bin/env python
from menus import Main
import sys, os
import argparse

		

def main():
	"""
	Main function
	"""
	parser = argparse.ArgumentParser(description="Start a Leviathan Server")
	parser.add_argument('--endpoint', help="Specific IP to bind the listener", required=True)
	parser.add_argument('--port', type=int, help="Port to use", required=True)
	parser.add_argument('--certfile', help="path to the cert file to use for SSL. Optional.")

	args = parser.parse_args()

	host = args.endpoint
	port = args.port

	if not args.certfile:
		server = Main.WinduServer(host, port, None)
	else:
		server = Main.WinduServer(host, port, args.certfile)

	server.run()
	MainMenu = Main.Menu()
	MainMenu.cmdloop()
	server.stop()

if __name__ == "__main__":
	main()