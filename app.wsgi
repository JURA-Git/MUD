

import sys
import os

# 1. Flask 앱 경로 추가
sys.path.insert(0, '/var/www/html/mud')

# 2. Flask 인스턴스를 WSGI가 인식할 수 있도록 지정
from app import app as application
