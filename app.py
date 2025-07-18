import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import pymysql

# 기본 설정
app = Flask(__name__)
app.secret_key = 'cvnFDzlx#jsDFjsCHBS'  # 필요시 변경
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MariaDB 연결 정보 (10.10.8.4)
DB_CONNECT = {
    'host': '10.10.8.4',
    'user': 'mud_db',
    'password': 'dkagh1.',
    'db': 'file_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# DB 커넥션 생성 함수
def get_connection():
    return pymysql.connect(**DB_CONNECT)

# 허용 파일 검사 (필요시 확장자 제한)
def allowed_file(filename):
    return filename != ''

@app.route('/')
def index():
    return render_template('index.html')

import os
from werkzeug.utils import secure_filename

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        description = request.form['description']
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            # 1) 원본 파일명 안전하게 정리
            orig_filename = secure_filename(file.filename)
            filename = orig_filename
            save_dir = app.config['UPLOAD_FOLDER']
            
            # 2) 동일 이름 체크 후, _1, _2, ... 증분 붙이기
            name, ext = os.path.splitext(orig_filename)
            counter = 1
            while os.path.exists(os.path.join(save_dir, filename)):
                filename = f"{name}_{counter}{ext}"
                counter += 1
            
            # 3) 최종 결정된 filename으로 저장
            save_path = os.path.join(save_dir, filename)
            file.save(save_path)

            # 4) DB에 저장할 때도 바뀐 filename 사용
            conn = get_connection()
            with conn.cursor() as cur:
                sql = "INSERT INTO files (description, filename) VALUES (%s, %s)"
                cur.execute(sql, (description, filename))
                conn.commit()
            conn.close()

            flash('파일이 업로드되었습니다.')
            return redirect(url_for('download'))
    return render_template('upload.html')


@app.route('/download')
def download():
    page      = request.args.get('page', 1, type=int)
    per_page  = 5
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
