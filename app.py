from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import cv2
import numpy as np
from scipy.signal import convolve2d
import zipfile
import uuid
import shutil
import pymysql
from functools import wraps
import jwt
from jwt import encode, decode
import datetime
from queue import Queue
import threading
import time
import logging
from logging.config import dictConfig

# 配置日志
dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'level': 'ERROR',
        'handlers': ['null']
    },
    'loggers': {
        'werkzeug': {
            'level': 'ERROR',
            'handlers': ['null'],
            'propagate': False,
        }
    }
})

# 禁用 Flask 默认的日志处理器
logging.getLogger('werkzeug').disabled = True

app = Flask(__name__)
CORS(app)

# 2. 添加获取客户端IP的函数
def get_client_ip():    
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
        return ip
    return request.remote_addr

# JWT配置
app.config['SECRET_KEY'] = 'your-secret-key'

# MySQL配置
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'ip_manager',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 基础文件夹配置
BASE_UPLOAD_FOLDER = 'uploads'
BASE_PROCESSED_FOLDER = 'processed'
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BASE_PROCESSED_FOLDER, exist_ok=True)

def get_db_connection():
    return pymysql.connect(**db_config)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '没有提供token!', 'status': 'error'}), 401
        try:
            token = token.split(' ')[1]
            decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'message': 'token无效!', 'status': 'error'}), 401
        return f(*args, **kwargs)
    return decorated

def linear_show(image, contrast_factor):
    low_percentile = np.percentile(image, contrast_factor * 100)
    high_percentile = np.percentile(image, 100 - contrast_factor * 100)
    return np.clip((image - low_percentile) * 255 / (high_percentile - low_percentile), 0, 255)

def process_image(file_path, white_area_threshold, black_area_threshold):
    try:
        ori = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if ori is None:
            return None

        if len(ori.shape) == 2:
            mask_1 = ori
        elif len(ori.shape) == 3:
            mask_1 = ori[:, :, 0]
        else:
            return None

        mask_1 = linear_show(mask_1, 0.03).astype(np.uint8)
        mask_1 = (mask_1 < 33).astype(np.uint8) * 255
        mask_1 = convolve2d(mask_1 > 0, np.ones((5, 5), dtype=np.uint8), mode='same')
        mask_1 = ((mask_1 > (5 * 5 / 2)) * 255).astype(np.uint8)

        if white_area_threshold > 0:
            white_isolated_mask, _ = detect_isolated_points(mask_1, white_area_threshold, False)
            mask_1[white_isolated_mask == 255] = 0

        if black_area_threshold > 0:
            black_isolated_mask, _ = detect_isolated_points(255 - mask_1, black_area_threshold, True)
            mask_1[black_isolated_mask == 255] = 255

        return mask_1
    except Exception as e:
        print(f"处理图像错误: {str(e)}")
        return None

def detect_isolated_points(image, area_threshold, detect_black=False):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(image, connectivity=8)
    error_flag = 0
    mask = np.zeros_like(image)

    for i in range(1, num_labels):
        connected_area = stats[i, -1]
        if connected_area <= area_threshold:
            error_flag = 1
            mask[labels == i] = 255

    return mask, error_flag

def is_ip_allowed(ip):
    try:
        # 首先检查白名单是否启用
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取白名单状态
        cursor.execute('SELECT enabled FROM whitelist_settings LIMIT 1')
        whitelist_result = cursor.fetchone()
        whitelist_enabled = bool(whitelist_result['enabled']) if whitelist_result else True
        
        print(f"检查IP: {ip}")
        print(f"白名单状态: {'启用' if whitelist_enabled else '禁用'}")
        
        if not whitelist_enabled:
            print("白名单已禁用，允许所有IP访问")
            cursor.close()
            conn.close()
            return True
            
        # 检查IP是否在白名单中
        cursor.execute('SELECT COUNT(*) as count FROM allowed_ips WHERE ip = %s', (ip,))
        result = cursor.fetchone()
        ip_count = result['count']
        
        cursor.close()
        conn.close()
        
        print(f"IP在白名单中的数量: {ip_count}")
        return ip_count > 0
        
    except Exception as e:
        print(f"检查IP错误: {str(e)}")
        return False

@app.route('/api/ips', methods=['GET', 'POST'])
@token_required
def manage_ips():
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM allowed_ips')
            ips = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return jsonify({
                'ips': ips,
                'status': 'success'
            })
        except Exception as e:
            print(f"获取IP列表错误: {str(e)}")
            return jsonify({
                'message': f'获取失败: {str(e)}',
                'status': 'error'
            }), 500
            
    elif request.method == 'POST':
        try:
            data = request.json
            if not data or not data.get('ip'):
                return jsonify({
                    'message': '请提供IP地址',
                    'status': 'error'
                }), 400

            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 检查IP是否已存在
            cursor.execute('SELECT COUNT(*) as count FROM allowed_ips WHERE ip = %s', (data['ip'],))
            result = cursor.fetchone()
            if result['count'] > 0:
                cursor.close()
                conn.close()
                return jsonify({
                    'message': 'IP已存在',
                    'status': 'error'
                }), 400

            # 添加新IP
            cursor.execute(
                'INSERT INTO allowed_ips (ip, description) VALUES (%s, %s)',
                (data['ip'], data.get('description', ''))
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'message': 'IP添加成功',
                'status': 'success'
            })
            
        except Exception as e:
            print(f"添加IP错误: {str(e)}")
            return jsonify({
                'message': f'添加失败: {str(e)}',
                'status': 'error'
            }), 500

@app.route('/api/whitelist/status', methods=['GET'])
@token_required
def get_whitelist_status_api():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT enabled FROM whitelist_settings LIMIT 1')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        enabled = bool(result['enabled']) if result else True
        return jsonify({
            'enabled': enabled,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@app.route('/api/whitelist/status', methods=['POST'])
@token_required
def update_whitelist_status():
    try:
        data = request.json
        if 'enabled' not in data:
            return jsonify({'message': '缺少enabled参数', 'status': 'error'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE whitelist_settings SET enabled = %s', 
                      (1 if data['enabled'] else 0,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': '设置更新成功',
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@app.route('/api/settings/threshold', methods=['GET', 'POST'])
def manage_threshold_settings():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            cursor.execute('SELECT white_threshold, black_threshold FROM default_settings LIMIT 1')
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return jsonify({
                'white_threshold': result['white_threshold'] if result else 0,
                'black_threshold': result['black_threshold'] if result else 0,
                'status': 'success'
            })
            
        elif request.method == 'POST':
            data = request.json
            if not data or 'white_threshold' not in data or 'black_threshold' not in data:
                return jsonify({
                    'message': '缺少必要的参数',
                    'status': 'error'
                }), 400
                
            # 更新设置
            cursor.execute('''
                UPDATE default_settings 
                SET white_threshold = %s, black_threshold = %s
                WHERE id = (SELECT id FROM (SELECT id FROM default_settings LIMIT 1) AS temp)
            ''', (data['white_threshold'], data['black_threshold']))
            
            # 如果没有记录，创建一条
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO default_settings (white_threshold, black_threshold)
                    VALUES (%s, %s)
                ''', (data['white_threshold'], data['black_threshold']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'message': '设置更新成功',
                'status': 'success'
            })
            
    except Exception as e:
        print(f"处理阈值设置错误: {str(e)}")
        return jsonify({
            'message': str(e),
            'status': 'error'
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        auth = request.json
        if not auth or not auth.get('username') or not auth.get('password'):
            return jsonify({'message': '请提供用户名和密码!', 'status': 'error'}), 401

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin_users WHERE username = %s AND password = %s', 
                      (auth.get('username'), auth.get('password')))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({'message': '用户名或密码错误!', 'status': 'error'}), 401

        token = encode(
            {
                'user': auth.get('username'),
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, 
            app.config['SECRET_KEY'],
            algorithm="HS256"
        )

        return jsonify({
            'token': token,
            'status': 'success',
            'message': '登录成功'
        })
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

# 全局任务队列
task_queue = Queue()
# 当前正在处理的任务ID
current_task_id = None
# 用于线程同步
task_lock = threading.Lock()

class TaskStatus:
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

# 任务状态存储
task_status = {}

def process_queue():
    global current_task_id
    while True:
        if not task_queue.empty():
            print_queue_status()  # 打印队列状态
            with task_lock:
                task_id = task_queue.get()
                current_task_id = task_id
                task_status[task_id]['status'] = TaskStatus.PROCESSING
                
            try:
                # 执行实际的处理逻辑
                result = process_task(task_status[task_id]['data'])
                task_status[task_id].update({
                    'status': TaskStatus.COMPLETED,
                    'result': result
                })
            except Exception as e:
                task_status[task_id].update({
                    'status': TaskStatus.FAILED,
                    'error': str(e)
                })
            finally:
                with task_lock:
                    current_task_id = None
        time.sleep(0.1)  # 避免CPU过度使用

def print_queue_status():
    """打印当前队列状态"""
    print("\n=== 队列状态 ===")
    print(f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"队列中任务数量: {task_queue.qsize()}")
    print(f"当前处理任务ID: {current_task_id}")
    print("\n任务详情:")
    
    # 按创建时间排序的任务列表
    sorted_tasks = sorted(
        task_status.items(),
        key=lambda x: x[1]['created_at']
    )
    
    for task_id, task in sorted_tasks:
        status_str = {
            TaskStatus.QUEUED: "等待中",
            TaskStatus.PROCESSING: "处理中",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败"
        }.get(task['status'], "未知状态")
        
        created_time = datetime.datetime.fromtimestamp(task['created_at']).strftime('%H:%M:%S')
        client_ip = task.get('client_ip', '未知IP')
        print(f"任务ID: {task_id[:8]}... | 状态: {status_str} | IP: {client_ip} | 创建时间: {created_time}")
    
    print("================\n")

# 启动队列处理线程
threading.Thread(target=process_queue, daemon=True).start()

@app.route('/api/process', methods=['POST'])
def process_zip():
    try:
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        client_ip = get_client_ip()
        
        print(f"\n=== 新任务添加 ===")
        print(f"任务ID: {task_id[:8]}...")
        print(f"客户端IP: {client_ip}")
        print(f"添加时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 保存上传文件并创建任务
        file = request.files['file']
        unique_id = str(uuid.uuid4())
        upload_folder = os.path.join(BASE_UPLOAD_FOLDER, unique_id)
        os.makedirs(upload_folder, exist_ok=True)
        
        zip_path = os.path.join(upload_folder, 'files.zip')
        file.save(zip_path)
        
        # 创建任务数据
        task_data = {
            'zip_path': zip_path,
            'upload_folder': upload_folder,
            'white_area_threshold': int(request.form.get('white_area_threshold', 0)),
            'black_area_threshold': int(request.form.get('black_area_threshold', 0))
        }
        
        # 将任务添加到队列
        task_status[task_id] = {
            'status': TaskStatus.QUEUED,
            'data': task_data,
            'created_at': time.time(),
            'client_ip': client_ip  # 保存客户端IP
        }
        task_queue.put(task_id)
        
        # 返回任务ID
        return jsonify({
            'task_id': task_id,
            'status': 'success',
            'message': '文件已上传，等待处理'
        })
        
    except Exception as e:
        return jsonify({
            'message': f'上传失败: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    if task_id not in task_status:
        return jsonify({
            'status': 'error',
            'message': '任务不存在'
        }), 404
        
    task = task_status[task_id]
    queue_position = 0
    
    if task['status'] == TaskStatus.QUEUED:
        # 计算队列位置：包括正在处理的任务和排在前面的等待任务
        current_time = time.time()
        
        # 如果有正在处理的任务，队列位置+1
        if current_task_id is not None:
            queue_position += 1
            
        # 计算排在前面的等待任务
        for t_id, t_info in task_status.items():
            if (t_info['status'] == TaskStatus.QUEUED and 
                t_info['created_at'] < task['created_at']):
                queue_position += 1
    
    response = {
        'status': task['status'],
        'queue_position': queue_position
    }
    
    if task['status'] == TaskStatus.COMPLETED and 'result' in task:
        response['result'] = task['result']
    elif task['status'] == TaskStatus.FAILED and 'error' in task:
        response['error'] = task['error']
    
    return jsonify(response)

def process_task(task_data):
    """处理单个任务的函数"""
    try:
        zip_path = task_data['zip_path']
        upload_folder = task_data['upload_folder']
        white_area_threshold = task_data['white_area_threshold']
        black_area_threshold = task_data['black_area_threshold']
        
        # 创建处理结果目录
        unique_id = os.path.basename(upload_folder)
        processed_folder = os.path.join(BASE_PROCESSED_FOLDER, unique_id)
        os.makedirs(processed_folder, exist_ok=True)
        
        # 解压ZIP文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(upload_folder)
            
        total_files = -1  # 初始化为-1，因为会包含ZIP文件本身
        processed_files = []
        
        # 处理所有符合条件的文件
        for root, _, files in os.walk(upload_folder):
            for file_name in files:
                total_files += 1
                if ((file_name.startswith('f_') and file_name.endswith('_p.tif')) or
                    (file_name.startswith('f_') and file_name.endswith('_P.tif')) or
                    (file_name.startswith('o_') and file_name.endswith('.tif'))):
                    try:
                        file_path = os.path.join(root, file_name)
                        mask_1 = process_image(file_path, white_area_threshold, black_area_threshold)
                        if mask_1 is not None:
                            output_file_name = file_name.replace(".tif", "_m.tif")
                            output_file_path = os.path.join(processed_folder, output_file_name)
                            cv2.imwrite(output_file_path, mask_1)
                            processed_files.append(output_file_name)
                    except Exception as e:
                        print(f"处理文件失败: {file_name}, 错误: {str(e)}")
                        continue
        
        # 创建结果ZIP文件
        zip_filename = f"{unique_id}_processed.zip"
        zip_filepath = os.path.join(BASE_PROCESSED_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for file_name in processed_files:
                file_path = os.path.join(processed_folder, file_name)
                zipf.write(file_path, arcname=file_name)
                
        # 清理临时文件
        shutil.rmtree(upload_folder)
        shutil.rmtree(processed_folder)
        
        return {
            'message': f'件处理完成,上传{total_files}个文件,处理{len(processed_files)}个文件',
            'zip_file': zip_filename,
            'total_files': total_files,
            'processed_files_count': len(processed_files)
        }
        
    except Exception as e:
        print(f"任务处理错误: {str(e)}")
        # 确保清理临时文件
        if 'upload_folder' in locals():
            shutil.rmtree(upload_folder, ignore_errors=True)
        if 'processed_folder' in locals():
            shutil.rmtree(processed_folder, ignore_errors=True)
        raise

@app.route('/api/download/<zip_filename>', methods=['GET'])
def download_zip(zip_filename):
    zip_filepath = os.path.join(BASE_PROCESSED_FOLDER, zip_filename)
    if os.path.exists(zip_filepath):
        return send_file(zip_filepath, as_attachment=True)
    return jsonify({'message': '文件不存在', 'status': 'error'}), 404

# 删除IP
@app.route('/api/ips/<int:ip_id>', methods=['DELETE'])
@token_required
def delete_ip(ip_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先检查IP是否存在
        cursor.execute('SELECT * FROM allowed_ips WHERE id = %s', (ip_id,))
        ip = cursor.fetchone()
        
        if not ip:
            cursor.close()
            conn.close()
            return jsonify({
                'message': 'IP不存在',
                'status': 'error'
            }), 404
            
        # 删除IP
        cursor.execute('DELETE FROM allowed_ips WHERE id = %s', (ip_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'IP删除成功',
            'status': 'success'
        })
    except Exception as e:
        print(f"删除IP错误: {str(e)}")
        return jsonify({
            'message': f'删除失败: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/change-password', methods=['POST'])
@token_required
def change_password():
    try:
        data = request.json
        if not data or not data.get('oldPassword') or not data.get('newPassword'):
            return jsonify({
                'message': '请提供旧密码和新密码',
                'status': 'error'
            }), 400

        # 从token中获取用户名
        token = request.headers.get('Authorization').split(' ')[1]
        user_data = decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        username = user_data['user']

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 验证旧密码
        cursor.execute('SELECT * FROM admin_users WHERE username = %s AND password = %s', 
                      (username, data.get('oldPassword')))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({
                'message': '旧密码错误',
                'status': 'error'
            }), 400

        # 更新密码
        cursor.execute('UPDATE admin_users SET password = %s WHERE username = %s',
                      (data.get('newPassword'), username))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': '密码修改成功',
            'status': 'success'
        })
    except Exception as e:
        print(f"修改密码错误: {str(e)}")
        return jsonify({
            'message': f'修改密码失败: {str(e)}',
            'status': 'error'
        }), 500

# 添加任务清理函数
def cleanup_old_tasks():
    """清理已完成的旧任务"""
    current_time = time.time()
    expired_tasks = []
    
    for task_id, task in task_status.items():
        # 清理超过30分钟的已完成或失败任务
        if (task['status'] in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
            current_time - task['created_at'] > 1800):  # 30分钟
            expired_tasks.append(task_id)
            
    for task_id in expired_tasks:
        del task_status[task_id]

# 启动定期清理线程
def start_cleanup_thread():
    while True:
        cleanup_old_tasks()
        time.sleep(300)  # 每5分钟清理一次

threading.Thread(target=start_cleanup_thread, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)