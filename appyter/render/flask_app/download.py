import os
import traceback
import urllib.request, urllib.error
from flask import request, copy_current_request_context, current_app, session
from flask_socketio import emit

from appyter.render.flask_app.socketio import socketio

from appyter.render.flask_app.util import secure_filename, secure_url

# remove user agent from urllib.request requests
_opener = urllib.request.build_opener()
_opener.addheaders = [('Accept', '*/*')]
urllib.request.install_opener(_opener)

# download from remote
@socketio.on('download_start')
def download(data):
  print('file download start')
  session_id = session[request.sid]['_session']
  session_dir = os.path.join(current_app.config['DATA_DIR'], session_id)
  os.makedirs(current_app.config['DATA_DIR'], exist_ok=True)
  os.makedirs(session_dir, exist_ok=True)
  name = data.get('name')
  url = secure_url(data.get('url'))
  filename = secure_filename(data.get('file'))
  # TODO: worry about files that are too big/long
  @copy_current_request_context
  def download_with_progress(name, url, path, filename, emit):
    emit('download_start', dict(name=name, filename=filename))
    try:
      _, response = urllib.request.urlretrieve(
        url, filename=path,
        reporthook=lambda chunk, chunk_size, total_size: emit(
          'download_progress', dict(
            name=name,
            chunk=chunk,
            chunk_size=chunk_size,
            total_size=total_size,
          )
        ),
      )
      # NOTE: this may become an issue if ever someone wants actual html
      assert response.get_content_type() != 'text/html', 'Expected data, got html'
    except Exception as e:
      print('download error')
      traceback.print_exc()
      emit('download_error', dict(name=name, filename=filename, url=url, error=str(e)))
    else:
      emit('download_complete', dict(name=name, filename=filename))
  #
  emit('download_queued', dict(name=name, filename=filename))
  socketio.start_background_task(
    download_with_progress,
    name=name,
    url=url,
    path=os.path.join(session_dir, filename),
    filename=filename,
    emit=emit,
  )

# upload from client
@socketio.on("siofu_start")
def siofu_start(data):
  print('file upload start')
  try:
    session_id = session[request.sid]['_session']
    session_dir = os.path.join(current_app.config['DATA_DIR'], session_id)
    filename = secure_filename(data.get('name'))
    os.makedirs(current_app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(session_dir, exist_ok=True)
    assert filename != '', 'Invalid Filename'
    session[request.sid] = dict(session[request.sid], **{
      'file_%d' % (data.get('id')): dict(data,
        name=filename,
        bytesLoaded=0,
        fh=open(os.path.join(session_dir, filename), 'wb'),
      ),
    })
    emit('siofu_ready', {
      'id': data.get('id'),
      'name': None,
    })
  except Exception as e:
    traceback.print_exc()
    emit('siofu_error', str(e))

@socketio.on("siofu_progress")
def siofu_progress(data):
  session[request.sid]['file_%d' % (data['id'])]['fh'].write(data['content'])
  emit("siofu_chunk", {
    'id': data['id'],
  })

@socketio.on("siofu_done")
def siofu_done(data):
  print('file upload complete')
  session[request.sid]['file_%d' % (data['id'])]['fh'].close()
  del session[request.sid]['file_%d' % (data['id'])]
  emit('siofu_complete', {
    'id': data['id'],
  })