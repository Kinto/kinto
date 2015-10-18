import argparse
import sys
import textwrap
import warnings
#import os
import subprocess
import cliquet
from pyramid.paster import bootstrap

def kinto_migrate(env):
	registry = env['registry']

	for backend in ('cache','storage','permission'):
		if hasattr(registry, backend):
			getattr(registry, backend).initialize_schema()

def main (args=None):
	"""The main routine."""
	if args is None:
		args = sys.argv[1:]
	
	parser = argparse.ArgumentParser(description="Kinto administration commands")
	subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands',help='init/start/migrate')
	
	parser_init = subparsers.add_parser('init') 
	parser_init.set_defaults(which='init') 

	parser_migrate = subparsers.add_parser('migrate') 
	parser_migrate.set_defaults(which='migrate') 

	parser_start = subparsers.add_parser('start') 
	parser_start.set_defaults(which='start') 

	args = vars(parser.parse_args())

	if args['which'] =='init':
		env =bootstrap('config/kinto.ini')
	elif args['which'] =='migrate':
		#subprocess.call(["python","-m","cliquet","--ini","config/kinto.ini","migrate"])
		print("running migrations")
	elif args['which'] =='start':
		subprocess.call(["python","-m","pyramid.scripts.pserve","config/kinto.ini","--reload"])		


if __name__ == "__main__":
	main()
