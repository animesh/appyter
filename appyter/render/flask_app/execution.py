import os
import sys
import traceback
import functools
from subprocess import PIPE
from flask import current_app, request, copy_current_request_context, session, abort
from flask_socketio import emit

from appyter.render.flask_app import socketio
from appyter.render.flask_app.core import core, post_index_html_dynamic, generate_session_id
from appyter.render.flask_app.util import sanitize_uuid

from appyter.context import get_jinja2_env
from appyter.render.nbconstruct import render_nb_from_nbtemplate

@socketio.on('session')
def _(data):
  if not data:
    print('creating new session')
    data = dict(
      _session=generate_session_id()
    )
    emit('session', data)
  print('session', data, request.sid)
  session[request.sid] = dict(session.get(request.sid, {}), _session=sanitize_uuid(data['_session']))
  print(session)

@socketio.on('disconnect')
def _():
  print('disconnect', request.sid)
  if request.sid in session:
    del session[request.sid]
  print(session)

@socketio.on('submit')
def submit(data):
  print('submit', data)
  # WARNING: this depends on FileFields taking care of filename sanity checking
  post_index_html_dynamic(data)
  # TODO: deal with possible redirect

@socketio.on('init')
def init(data):
  print('init')
  session_id = sanitize_uuid(data.get('_session'))
  if session_id is None:
    abort(404)
    return
  session_dir = os.path.join(current_app.config['DATA_DIR'], session_id)
  emit('status', 'Notebook created, queuing execution')
  if not current_app.config['DEBUG']:
    from eventlet.green.subprocess import Popen
  else:
    from subprocess import Popen
  socketio.start_background_task(
    copy_current_request_context(nbexecute),
    cwd=session_dir,
    ipynb=current_app.config['IPYNB'],
    emit=emit,
    Popen=Popen,
  )

def nbexecute(cwd='', ipynb='', emit=print, Popen=None):
  import json
  if Popen is None:
    from subprocess import Popen
  with Popen(
    [
      sys.executable,
      '-u',
      '-m', 'appyter',
      'nbexecute',
      '--cwd='+cwd,
      ipynb,
    ],
    env=dict(
      PYTHONPATH=':'.join(sys.path),
      PATH=os.environ['PATH'],
    ),
    stdout=PIPE,
  ) as proc:
    packet = proc.stdout.readline()
    while packet:
      msg = json.loads(packet)
      emit(msg['type'], msg['data'])
      packet = proc.stdout.readline()