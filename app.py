import os
import requests
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort, session
from werkzeug.utils import secure_filename
import pymysql

# 기본 설정
app = Flask(__name__)
app.secret_key = 'cvnFDzlx#jsDFjsCHBS'# 세션용

# 카카오 REST API 키
KAKAO_CLIENT_ID = '4391fd5ee9201b61b52bb1ce7c474e9f'
#tYbp306dHUMFOLjNl6NceuiUB8cGQ072' 카카오 클라이언트 키
KAKAO_REDIRECT_URI = 'http://10.10.8.3/oauth/callback/kakao'


# 1) 업로드 크기 제한: 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
# 업로드 폴더 설정
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
                



# MariaDB 연결 정보
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

# 허용 파일 검사
def allowed_file(filename):
    if not filename:
        return False
    # null byte 차단
    if '\x00' in filename:
        return False
    # 확장자 검사
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXT
## 카카오 인증절차 ########################################################################
## 카카오 OAuth 인증 처리
@app.route('/oauth/kakao')
def kakao_oauth():
    # 카카오 인증 URL 생성
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return redirect(kakao_auth_url)

## 카카오 OAuth 콜백 처리
@app.route('/oauth/callback/kakao')
def callback_kakao():
    code = request.args.get('code')
    if not code:
        flash('인증 코드가 없습니다.')
        return redirect(url_for('index'))

    # 카카오 토큰 요청
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
        flash('액세스 토큰이 없습니다.')
        return redirect(url_for('index'))

    # 세션에 토큰 저장
    session['kakao_access_token'] = access_token
    flash('카카오 인증 성공')
    return redirect(url_for('index'))
@app.route('/logout')
def logout():
    # 세션에서 카카오 액세스 토큰 제거
    session.pop('kakao_access_token', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('index'))
## 카카오 인증절차 ########################################################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        description = request.form.get('description', '')
        file = request.files.get('file')

        # 1. 유효성 검사: 확장자 + 0 byte 검사
        if not file or not allowed_file(file.filename):
            flash('허용되지 않는 파일입니다.(확장자 및 null 파일 검사)')
            return redirect(request.url)

        # 2. 원본 파일명에서 안전한 저장용 이름 생성
        orig_filename = file.filename
        filename = secure_filename(orig_filename)

        # 3. 중복 방지
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{name}_{counter}{ext}"
            counter += 1

        # 4. 파일 저장
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(save_path)
        except Exception:
            abort(500, '파일 저장 실패')

        # 5. DB 저장 (secure_filename 이름만 저장)
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO files (description, filename) VALUES (%s, %s)",
                (description, filename)
            )
            conn.commit()
        conn.close()

        flash('파일이 업로드되었습니다.')
        return redirect(url_for('download'))

    return render_template('upload.html')


@app.route('/download')
def download():
    page      = request.args.get('page', 1, type=int)
    per_page  = 10
    offset    = (page - 1) * per_page

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM files")
        total = cur.fetchone()['cnt']
        cur.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT %s OFFSET %s",
            (per_page, offset)
        )
        files = cur.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('download.html',
                           files=files,
                           page=page,
                           total_pages=total_pages)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], 
                               filename,
                               as_attachment=True)#다운로드 팝업뜨게만들기

@app.route('/delete/<int:file_id>')
def delete(file_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM files WHERE id=%s", (file_id,))
        row = cur.fetchone()
        if row:
            # 파일 삭제
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], row['filename']))
            except FileNotFoundError:
                pass
            # DB 레코드 삭제
            cur.execute("DELETE FROM files WHERE id=%s", (file_id,))
            conn.commit()
    conn.close()
    return redirect(url_for('download'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


############ 로그인 없이 접근 가능한 경로 설정

# 로그인 없이 접근 가능한 경로 (예외 처리)
PUBLIC_PATHS = [
    '/',                # 메인페이지
    '/login/kakao',     # 로그인 시도
    '/oauth/callback/kakao',  # 로그인 콜백
    '/static/',         # 정적 파일
    '/favicon.ico'
]

######################################로그인 체크 데코레이터######################################
@app.before_request
def check_login():
    # 로그인 되어 있으면 통과
    if session.get('user'):
        return

    # 로그인 없이 허용된 경로는 통과
    for path in PUBLIC_PATHS:
        if request.path.startswith(path):
            return

    # 로그인 안 되어 있고 보호 경로라면 → 메인 페이지로
    return redirect(url_for('index'))
######################################로그인 체크 데코레이터######################################