import os
import sys
import uuid
import json
import time
from threading import Lock
from flask import Flask, request, abort, render_template, current_app, copy_current_request_context
from flask_socketio import SocketIO, emit
from jupyter_template.context import get_jinja2_env
from jupyter_template.parse.nbtemplate import nbtemplate_from_ipynb_file
from jupyter_template.render.form import render_form_from_nbtemplate
from jupyter_template.render.nbviewer import render_nbviewer_from_nb
from jupyter_template.render.ipynb import render_nb_from_nbtemplate
from jupyter_template.render.json import render_nbtemplate_json_from_nbtemplate
from jupyter_template.render.nbexecutor import render_nbexecutor_from_nb
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
load_dotenv()

PREFIX = os.environ.get('PREFIX', '/')
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = json.loads(os.environ.get('PORT', '5000'))
DATA_DIR = os.environ.get('DATA_DIR', 'data')
SECRET_KEY = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
kargs = dict([arg[2:].split('=', maxsplit=1) for arg in sys.argv[1:] if arg.startswith('--')])

nbtemplate = nbtemplate_from_ipynb_file(args[0])

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app)

thread = None
thread_lock = Lock()

def get_index_html():
  ''' Return options as form
  '''
  env = get_jinja2_env(cwd=kargs.get('cwd', os.getcwd()))
  return render_form_from_nbtemplate(env, nbtemplate)

def get_index_json():
  ''' Return options as json
  '''
  env = get_jinja2_env(cwd=kargs.get('cwd', os.getcwd()))
  return render_nbtemplate_json_from_nbtemplate(env, nbtemplate)

def post_index_html_dynamic(data):
  ''' Return dynamic nbviewer
  '''
  env = get_jinja2_env(context=data, cwd=kargs.get('cwd', os.getcwd()))
  nb = render_nb_from_nbtemplate(env, nbtemplate)
  return render_template(
    'dynamic.j2',
    _nbviewer=render_nbviewer_from_nb(env, nb),
    _data=json.dumps(data),
  )

def post_index_html_static(data):
  ''' Return static nbviewer
  '''
  env = get_jinja2_env(context=data, cwd=kargs.get('cwd', os.getcwd()))
  nb = render_nb_from_nbtemplate(env, nbtemplate)
  return render_nbviewer_from_nb(env, nb)

def post_index_json_static(data):
  ''' Return rendered json
  '''
  env = get_jinja2_env(context=data, cwd=kargs.get('cwd', os.getcwd()))
  nb = render_nb_from_nbtemplate(env, nbtemplate)
  return render_nbtemplate_json_from_nbtemplate(env, nb)

def post_index_ipynb_static(data):
  ''' Return rendered ipynb
  '''
  env = get_jinja2_env(context=data, cwd=kargs.get('cwd', os.getcwd()))
  nb = render_nb_from_nbtemplate(env, nbtemplate)
  return render_nb_from_nbtemplate(env, nb)

def prepare_formdata(req):
  # Get form variables
  session_id = str(uuid.uuid4())
  session_dir = os.path.join(DATA_DIR, session_id)
  data = req.form.to_dict()
  # Process upload files
  for fname, fh in req.files.items():
    # Save files to datadir for session
    filename = secure_filename(fh.filename)
    os.makedirs(session_dir)
    fh.save(os.path.join(session_dir, filename))
    data[fname] = filename
  return dict(**data, _session_dir=session_dir)

@app.route(PREFIX, methods=['GET'])
def get_index():
  mimetype = request.accept_mimetypes.best_match([
    'text/html',
    'application/vnd.jupyter', 'application/vnd.jupyter.cells', 'application/x-ipynb+json',
    'application/json',
  ], 'text/html')
  if mimetype in {'text/html'}:
    return get_index_html()
  elif mimetype in {'application/vnd.jupyter', 'application/vnd.jupyter.cells', 'application/x-ipynb+json'}:
    return nbtemplate
  elif mimetype in {'application/json'}:
    return get_index_json()
  abort(404)

@app.route(PREFIX, methods=['POST'])
def post_index():
  mimetype = request.accept_mimetypes.best_match([
    'text/html',
    'application/vnd.jupyter', 'application/vnd.jupyter.cells', 'application/x-ipynb+json',
    'application/json',
  ], 'text/html')
  if mimetype in {'text/html'}:
    if request.args.get('static') is not None:
      return post_index_html_static(request.form.to_dict())
    else:
      return post_index_html_dynamic(prepare_formdata(request))
  elif mimetype in {'application/vnd.jupyter', 'application/vnd.jupyter.cells', 'application/x-ipynb+json'}:
    return post_index_ipynb_static(request.form.to_dict())
  elif mimetype in {'application/json'}:
    return post_index_json_static(request.form.to_dict())
  abort(404)

def cleanup():
  global thread
  with thread_lock:
    thread = None

@socketio.on('init')
def init(data):
  # TODO: Enable more than one thread
  env = get_jinja2_env(context=data, cwd=kargs.get('cwd', os.getcwd()))
  nb = render_nb_from_nbtemplate(env, nbtemplate)
  nbexecutor = copy_current_request_context(render_nbexecutor_from_nb(env, nb))
  global thread
  while True:
    with thread_lock:
      if not thread:
        thread = socketio.start_background_task(
          nbexecutor, emit, cleanup
        )
        break
    emit('status', 'Waiting for server...')
    time.sleep(1)


def main():
  return socketio.run(
      app,
      host=HOST,
      port=PORT,
  )

if __name__ == '__main__':
  main()