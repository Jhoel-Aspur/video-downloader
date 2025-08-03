from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import os
import tempfile
import shutil
import logging
from threading import Thread
from pathlib import Path
import re

app = Flask(__name__)

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directorio de descargas
DOWNLOAD_DIR = os.path.join(os.getcwd(), "descargas")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Variable global para progreso
progress_data = {'percent': 0, 'status': 'idle', 'filename': '', 'message': ''}

def is_valid_url(url):
    """Validate URL for supported platforms."""
    return bool(re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be|facebook\.com|tiktok\.com)/', url))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/youtube')
def youtube():
    return render_template('youtube.html')

@app.route('/facebook')
def facebook():
    return render_template('facebook.html')

@app.route('/tiktok')
def tiktok():
    return render_template('tiktok.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    platform = request.form['platform']
    formato = request.form['format']
    calidad = request.form.get('quality', 'best')

    if not is_valid_url(url):
        return jsonify({'success': False, 'error': 'URL no válida'}), 400

    # Force MP4 for TikTok
    if platform == 'tiktok' and formato != 'mp4':
        return jsonify({'success': False, 'error': 'TikTok solo soporta formato MP4'})

    global progress_data
    progress_data = {'percent': 0, 'status': 'downloading', 'filename': '', 'message': 'Conectando...'}

    def run_download():
        temp_dir = tempfile.mkdtemp()
        try:
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                'retries': 15,
                'fragment_retries': 15,
                'http_timeout': 60,
                'socket_timeout': 60,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ffmpeg_location': shutil.which('ffmpeg') or r'C:\Users\DESKTOP\Desktop\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe',
                'verbose': True,
            }

            # Enhanced cookie handling
            if os.path.exists('cookies.txt'):
                ydl_opts['cookiefile'] = os.path.join(os.getcwd(), 'cookies.txt')
            else:
                ydl_opts['cookiesfrombrowser'] = ('chrome', None, None, None)

            if formato == 'mp3':
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                quality_map = {
                    '144p': 'bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                }
                ydl_opts['format'] = quality_map.get(calidad, 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best')
                ydl_opts['merge_output_format'] = 'mp4'
                if platform != 'tiktok':
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                    ydl_opts['postprocessor_args'] = {
                        'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-strict', '-2']
                    }

            if platform == 'tiktok':
                ydl_opts['extractor_args'] = {
                    'tiktok': {
                        'app_version': '34.0.1',
                        'wait_for_video': 20,
                        'dynamic': True,
                        'check_formats': 'selected',
                    }
                }
                ydl_opts['http_headers'] = {
                    'Referer': 'https://www.tiktok.com/',
                    'Origin': 'https://www.tiktok.com',
                }
            elif platform == 'facebook':
                ydl_opts['extractor_args'] = {'facebook': {'wait': 15, 'verbose': True}}

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                progress_data['message'] = 'Extrayendo video...'
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                if formato == 'mp3':
                    filename = filename.rsplit('.', 1)[0] + '.mp3'
                else:
                    filename = filename.rsplit('.', 1)[0] + '.mp4'

            final_path = os.path.join(DOWNLOAD_DIR, os.path.basename(filename))
            shutil.copy(filename, final_path)
            shutil.rmtree(temp_dir)

            progress_data['status'] = 'completed'
            progress_data['filename'] = os.path.basename(final_path)
            progress_data['message'] = f"Descarga completada: {os.path.basename(final_path)}"
            logger.info(f"✅ Descarga completada: URL={url}, Platform={platform}, File={final_path}")

        except yt_dlp.DownloadError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            progress_data['status'] = 'error'
            progress_data['filename'] = ''
            progress_data['message'] = f"Error en la descarga: {str(e)}"
            logger.error(f"❌ Error en la descarga: URL={url}, Platform={platform}, Error={str(e)}")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            progress_data['status'] = 'error'
            progress_data['filename'] = ''
            progress_data['message'] = f"No se pudo descargar el video: {str(e)}"
            logger.error(f"❌ Error inesperado: URL={url}, Platform={platform}, Error={str(e)}")

    Thread(target=run_download).start()
    return jsonify({'success': True, 'message': 'Descarga iniciada'})

@app.route('/progress')
def get_progress():
    return jsonify(progress_data)

@app.route('/download_file/<filename>')
def serve_file(filename):
    safe_filename = Path(filename).name
    try:
        return send_from_directory(DOWNLOAD_DIR, safe_filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404

def progress_hook(d):
    global progress_data
    if d['status'] == 'downloading':
        porcentaje = d.get('_percent_str', '').strip().replace('%', '')
        try:
            progress_data['percent'] = float(porcentaje)
            progress_data['message'] = f"Descargando: {progress_data['percent']:.1f}%"
        except:
            progress_data['percent'] = 0
            progress_data['message'] = "Procesando..."
    elif d['status'] == 'finished':
        progress_data['message'] = "Procesando archivo..."

if __name__ == '__main__':
    app.run(debug=True)