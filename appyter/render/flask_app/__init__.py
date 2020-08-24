import os
import uuid
import click

from appyter.cli import cli
# from appyter.ext.flask_aiohttp import AioHTTP

def create_app(**kwargs):
  ''' Completely initialize the flask application
  '''
  from aiohttp import web
  from aiohttp_wsgi import WSGIHandler
  #
  from flask import Flask, Blueprint, current_app
  from flask_cors import CORS
  #
  from appyter.render.flask_app.socketio import socketio
  from appyter.render.flask_app.core import core
  import appyter.render.flask_app.static
  import appyter.render.flask_app.download
  import appyter.render.flask_app.execution
  #
  from appyter.context import get_env, find_blueprints
  from appyter.util import join_routes
  config = get_env(**kwargs)
  #
  print('Initializing aiohttp...')
  app = web.Application()
  app['config'] = config
  #
  print('Initializing socketio...')
  socketio.attach(app)
  #
  print('Initializing flask...')
  flask_app = Flask(__name__, static_url_path=None, static_folder=None)
  CORS(flask_app)
  flask_app.config.update(config)
  flask_app.debug = config['DEBUG']
  #
  if flask_app.config['PROXY']:
    print('wsgi proxy fix...')
    from werkzeug.middleware.proxy_fix import ProxyFix
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1)
  #
  print('Registering blueprints...')
  flask_app.register_blueprint(core, url_prefix=flask_app.config['PREFIX'])
  for blueprint_name, blueprint in find_blueprints(config=flask_app.config).items():
    if isinstance(blueprint, Blueprint):
      flask_app.register_blueprint(blueprint, url_prefix=join_routes(flask_app.config['PREFIX'], blueprint_name))
    elif callable(blueprint):
      blueprint(flask_app, url_prefix=join_routes(flask_app.config['PREFIX'], blueprint_name), DATA_DIR=flask_app.config['DATA_DIR'])
    else:
      raise Exception('Unrecognized blueprint type: ' + blueprint_name)
  #
  print('Registering flask with aiohttp...')
  wsgi_handler = WSGIHandler(flask_app)
  app.router.add_route('*', '/{path_info:.*}', wsgi_handler)
  return app

# register flask_app with CLI
@cli.command(help='Run a flask web application based on an appyter-enabled jupyter notebook')
@click.option('--cwd', envvar='CWD', default=os.getcwd(), help='The directory to treat as the current working directory for templates and execution')
@click.option('--prefix', envvar='PREFIX', default='/', help='Specify the prefix for which to mount the webserver onto')
@click.option('--profile', envvar='PROFILE', default='default', help='Specify the profile to use for rendering')
@click.option('--extras', envvar='EXTRAS', default=[], type=str, multiple=True, help='Specify extras flags')
@click.option('--host', envvar='HOST', default='127.0.0.1', help='The host the flask server should run on')
@click.option('--port', envvar='PORT', type=int, default=5000, help='The port this flask server should run on')
@click.option('--proxy', envvar='PROXY', type=bool, default=False, help='Whether this is running behind a proxy and the IP should be fixed for CORS')
@click.option('--data-dir', envvar='DATA_DIR', default='data', help='The directory to store data of executions')
@click.option('--dispatcher', envvar='DISPATCHER', type=str, help='The URL to the dispatcher, otherwise use an embedded dispatcher')
@click.option('--secret-key', envvar='SECRET_KEY', default=str(uuid.uuid4()), help='A secret key for flask')
@click.option('--debug', envvar='DEBUG', type=bool, default=True, help='Whether or not we should be in debugging mode, not for use in multi-tenant situations')
@click.option('--static-dir', envvar='STATIC_DIR', default='static', help='The folder whether staticfiles are located')
@click.option('--keyfile', envvar='KEYFILE', default=None, help='The SSL certificate private key for wss support')
@click.option('--certfile', envvar='CERTFILE', default=None, help='The SSL certificate public key for wss support')
@click.argument('ipynb', envvar='IPYNB')
def flask_app(*args, **kwargs):
  # write all config to env
  os.environ.update(
    CWD=str(kwargs.get('cwd')),
    PREFIX=str(kwargs.get('prefix')),
    PROFILE=str(kwargs.get('profile')),
    EXTRA=str(kwargs.get('extras')),
    HOST=str(kwargs.get('host')),
    PORT=str(kwargs.get('port')),
    PROXY=str(kwargs.get('proxy')),
    DATA_DIR=str(kwargs.get('data_dir')),
    DISPATCHER=str(kwargs.get('dispatcher')),
    SECRET_KEY=str(kwargs.get('secret_key')),
    DEBUG=str(kwargs.get('debug')),
    STATIC_DIR=str(kwargs.get('static_dir')),
    KEYFILE=str(kwargs.get('keyfile')),
    CERTFILE=str(kwargs.get('certfile')),
    IPYNB=str(kwargs.get('ipynb')),
  )
  if kwargs.get('debug'):
    from aiohttp_devtools.logs import setup_logging
    from aiohttp_devtools.runserver import runserver, run_app
    setup_logging(True)
    run_app(*runserver(app_path=__file__))
  else:
    from aiohttp import web
    app = create_app(**kwargs)
    return web.run_app(app)
