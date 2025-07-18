import os
import requests
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort, session
from werkzeug.utils import secure_filename
import pymysql

app = Flask(__name__)
app.secret_key = 'cvnFDzlx#jsDFjsCHBS'

# 카카오 OAuth 설정
KAKAO_CLIENT_ID = '4391fd5ee9201b61b52bb1ce7c474e9f'
KAKAO_REDIRECT_URI = 'http://10.10.8.3/oauth/callback/kakao'

# 업로드 설정
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 2) 허용 확장자
ALLOWED_EXT = { 
                # 이미지 파일
                'jpg', 'jpeg', 'png', 'gif', 'svg',
                # 압축/아카이브
                'zip', 'rar', '7z',
                'tar', 'gz', 'bz2', 'xz',
                'tar.gz', 'tar.bz2', 'tar.xz',
                # 문서/오피스/텍스트
                'txt', 'pdf',
                'doc', 'docx',
                'xls', 'xlsx', 'xlsb',
                'ppt', 'pptx',
                # 설정/로그
                'yaml', 'yml',
                'json', 'xml',
                'ini', 'conf', 'log',
                # 코드/스크립트
                'py', 'java', 'c', 'cpp', 'h',
                'sh', 'bash', 'zsh', 'fish',
                'bat', 'cmd',
                'plsql', 'tcl', 'awk', 'sed',
                'makefile', 'cmake',
                # 빌드 도구/패키지 매니저
                'gradle', 'ant', 'sbt',
                'npm', 'yarn',
                'dockerfile',
                # 인프라/자동화(IaC)
                'kubernetes', 'helm',
                'terraform',
                'ansible', 'chef', 'puppet', 'saltstack',
                'cloudformation',
                # API 명세
                'openapi', 'swagger', 'graphql',
                # 데이터베이스 덤프/파일
                'sql', 'db',
                'sqlite', 'h2',
                'dbf', 'mdb', 'accdb',
                # 이진 직렬화/포맷
                'protobuf', 'avro',
                'parquet', 'orc',
                'thrift', 'capnp',
                'msgpack', 'bson', 'cbor',
                'flatbuffers',
                'sbe', 'fix', 'x12', 'edi',
                # 데이터베이스 서비스 클라이언트
                'postgresql', 'mysql', 'mariadb',
                'oracle', 'sqlserver', 'db2',
                'cassandra', 'mongodb', 'redis',
                'elasticsearch', 'couchbase',
                'dynamodb', 'bigtable', 'hbase',
                'neo4j', 'arango', 'orientdb',
                'couchdb', 'riak',
                'influxdb', 'timescaledb',
                'clickhouse', 'presto', 'trino',
                }
# set().union(*ALLOWED_EXT.values())
                



# DB 설정
DB_CONNECT = {
    'host': '10.10.8.4',
    'user': 'mud_db',
    'password': 'dkagh1.',
    'db': 'file_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_connection():
    return pymysql.connect(**DB_CONNECT)

def allowed_file(filename):
    if not filename or '\x00' in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXT

# 로그인 필요 없는 경로
PUBLIC_PATHS = ['/', '/oauth/kakao', '/oauth/callback/kakao', '/static/', '/favicon.ico']

@app.before_request
def check_login():
    if session.get('kakao_access_token'):
        return
    for path in PUBLIC_PATHS:
        if request.path.startswith(path):
            return
    return redirect(url_for('index'))

# 루트 페이지 = 로그인 페이지
@app.route('/')
def index():
    return render_template('login.html')

# 카카오 로그인 시작
@app.route('/oauth/kakao')
def kakao_oauth():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return redirect(kakao_auth_url)

# 카카오 로그인 콜백
@app.route('/oauth/callback/kakao')
def callback_kakao():
    code = request.args.get('code')
    if not code:
        flash('인증 코드가 없습니다.')
        return redirect(url_for('index'))

    token_url = 'https://kauth.kakao.com/oauth/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': KAKAO_CLIENT_ID,
        'redirect_uri': KAKAO_REDIRECT_URI,
        'code': code
    }

    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        flash('토큰 요청 실패')
        return redirect(url_for('index'))

    token_info = response.json()
    access_token = token_info.get('access_token')
    if not access_token:
        flash('토큰 없음')
        return redirect(url_for('index'))

    session['kakao_access_token'] = access_token
    flash('카카오 인증 성공')
    return redirect(url_for('main_page'))

# 메인 페이지 (기존 index.html → main.html)
@app.route('/main')
def main_page():
    return render_template('main.html')

# 로그아웃
@app.route('/logout')
def logout():
    session.pop('kakao_access_token', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('index'))

# 파일 업로드
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        description = request.form.get('description', '')
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            flash('허용되지 않는 파일입니다.')
            return redirect(request.url)

        orig_filename = file.filename
        filename = secure_filename(orig_filename)

        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{name}_{counter}{ext}"
            counter += 1

        try:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except:
            abort(500, '파일 저장 실패')

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO files (description, filename) VALUES (%s, %s)", (description, filename))
            conn.commit()
        conn.close()

        flash('업로드 완료')
        return redirect(url_for('download'))

    return render_template('upload.html')

# 다운로드 목록
@app.route('/download')
def download():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM files")
        total = cur.fetchone()['cnt']
        cur.execute("SELECT * FROM files ORDER BY id DESC LIMIT %s OFFSET %s", (per_page, offset))
        files = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('download.html', files=files, page=page, total_pages=total_pages)

# 파일 다운로드 링크
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# 파일 삭제
@app.route('/delete/<int:file_id>')
def delete(file_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM files WHERE id=%s", (file_id,))
        row = cur.fetchone()
        if row:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], row['filename']))
            except FileNotFoundError:
                pass
            cur.execute("DELETE FROM files WHERE id=%s", (file_id,))
            conn.commit()
    conn.close()
    return redirect(url_for('download'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)