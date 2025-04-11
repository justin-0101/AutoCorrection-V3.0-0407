#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from app import create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    # 确保使用UTF-8编码
    import sys
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None
    
    # 运行应用
    app.run(host='0.0.0.0', debug=True) 