from flask import Blueprint, request, jsonify
import os
import json

config_bp = Blueprint('config', __name__)

@config_bp.route('/api/website-config', methods=['POST'])
def save_website_config():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['projectName', 'rootDir']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        # 验证根目录是否存在
        if not os.path.exists(data['rootDir']):
            return jsonify({
                'success': False,
                'message': '指定的根目录不存在'
            }), 400
            
        # 处理SSL证书文件
        ssl_config = {}
        if data.get('sslEnabled'):
            ssl_files = request.files
            if 'sslCert' in ssl_files and 'sslKey' in ssl_files:
                # 保存SSL证书文件
                cert_path = os.path.join(data['rootDir'], 'ssl', 'cert.pem')
                key_path = os.path.join(data['rootDir'], 'ssl', 'key.pem')
                
                os.makedirs(os.path.join(data['rootDir'], 'ssl'), exist_ok=True)
                ssl_files['sslCert'].save(cert_path)
                ssl_files['sslKey'].save(key_path)
                
                ssl_config = {
                    'certPath': cert_path,
                    'keyPath': key_path
                }
        
        # 创建配置对象
        config = {
            'projectName': data['projectName'],
            'rootDir': data['rootDir'],
            'notes': data.get('notes', ''),
            'sslEnabled': data.get('sslEnabled', False),
            'sslConfig': ssl_config if data.get('sslEnabled') else {}
        }
        
        # 保存配置到文件
        config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, f"{data['projectName']}.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        return jsonify({
            'success': True,
            'message': '配置保存成功',
            'config': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存配置时出错: {str(e)}'
        }), 500