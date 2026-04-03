from flask import Flask, render_template, request, jsonify
import json
import re
import redis
import pymysql
import psycopg2
import op_redis
from db import init_db, get_configs, get_config_by_id, add_config, update_config, delete_config, get_history

app = Flask(__name__)

# Pattern validation
# 第1段 配置项大类 -> 0-9 + 大写字母A-Z 固定一位字母
# 第2段 配置项简称 -> 固定三位字母或数字 (assuming case insensitive matching or standard alphanumeric)
# 第3段 配置项序号 -> 固定4位，数字或字母
pattern_category = re.compile(r'^[0-9A-Z]$')
pattern_abbr = re.compile(r'^[0-9a-zA-Z]{3}$')
pattern_seq = re.compile(r'^[0-9a-zA-Z]{4}$')

@app.before_request
def before_first_request():
    if not hasattr(app, 'db_initialized'):
        init_db()
        app.db_initialized = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manual_config')
def manual_config():
    return render_template('manual_config.html')

@app.route('/check_redis')
def check_redis():
    return render_template('check_redis.html')

@app.route('/api/configs', methods=['GET'])
def api_get_configs():
    filters = {
        'config_id': request.args.get('config_id'),
        'category': request.args.get('category'),
        'abbr': request.args.get('abbr'),
        'seq': request.args.get('seq'),
        'keyword': request.args.get('keyword'),
        'update_time_start': request.args.get('update_time_start'),
        'update_time_end': request.args.get('update_time_end'),
    }
    configs = get_configs(filters)
    # Datatables format
    return jsonify({"data": configs})

@app.route('/api/config', methods=['POST'])

def api_add_config():
    data = request.json
    config_id = data.get('config_id', '')
    description = data.get('description', '')
    param_desc = data.get('param_desc', '')
    content_str = data.get('content', '')
    
    if len(config_id) != 8:
        return jsonify({"success": False, "msg": "配置项编号必须是8位长度！"}), 400
        
    category = config_id[0]
    abbr = config_id[1:4]
    seq = config_id[4:8]
    
    if not pattern_category.match(category):
         return jsonify({"success": False, "msg": "配置项大类必须是0-9或大写字母A-Z！"}), 400
    if not pattern_abbr.match(abbr):
         return jsonify({"success": False, "msg": "配置项简称必须是3位字母或数字！"}), 400
    if not pattern_seq.match(seq):
         return jsonify({"success": False, "msg": "配置项序号必须是4位数字或字母！"}), 400
         
    # Validate JSON
    try:
        content_json = json.loads(content_str)
        content_serialized = json.dumps(content_json, ensure_ascii=False)
    except json.JSONDecodeError:
        return jsonify({"success": False, "msg": "配置项内容必须是合法的JSON格式！"}), 400
    
    # Check if exists
    if get_config_by_id(config_id):
        return jsonify({"success": False, "msg": "该配置项编号已存在！"}), 400
        
    success = add_config(config_id, category, abbr, seq, description, param_desc, content_serialized)
    if success:
        return jsonify({"success": True, "msg": "添加成功"})
    else:
        return jsonify({"success": False, "msg": "添加失败，数据库错误"}), 500

@app.route('/api/config/<config_id>', methods=['PUT', 'DELETE'])
def api_edit_config(config_id):
    if request.method == 'PUT':
        data = request.json
        description = data.get('description', '')
        param_desc = data.get('param_desc', '')
        content_str = data.get('content', '')
        
        try:
            content_json = json.loads(content_str)
            content_serialized = json.dumps(content_json, ensure_ascii=False)
        except json.JSONDecodeError:
            return jsonify({"success": False, "msg": "配置项内容必须是合法的JSON格式！"}), 400
            
        success = update_config(config_id, description, param_desc, content_serialized)
        if success:
            return jsonify({"success": True, "msg": "更新成功"})
        else:
            return jsonify({"success": False, "msg": "更新失败"}), 500
            
    elif request.method == 'DELETE':
        success = delete_config(config_id)
        if success:
            return jsonify({"success": True, "msg": "删除成功"})
        else:
            return jsonify({"success": False, "msg": "删除失败"}), 500

@app.route('/api/config/<config_id>/history', methods=['GET'])
def api_get_history(config_id):
    history = get_history(config_id)
    return jsonify({"data": history})

@app.route('/api/redis/get_config', methods=['GET'])
def api_redis_get_config():
    config = get_config_by_id('SRDS0000')
    if not config:
        return jsonify({"success": False, "msg": "未找到 SRDS0000 配置项"}), 400
    try:
        content_json = json.loads(config['content'])
        redis_main = content_json.get('redis-main')
        if not redis_main:
            return jsonify({"success": False, "msg": "SRDS0000 中没有名为 'redis-main' 的项"}), 400
        return jsonify({"success": True, "data": redis_main})
    except json.JSONDecodeError:
        return jsonify({"success": False, "msg": "SRDS0000 的内容不是合法的JSON格式"}), 400

@app.route('/api/redis/test_connection', methods=['POST'])
def api_redis_test_connection():
    data = request.json
    try:
        host = data.get('host', '127.0.0.1')
        port = int(data.get('port', 6379))
        decode_responses = data.get('decode_responses', True)
        
        channel_count = op_redis.get_channel_count(host=host, port=port, db=0)
        return jsonify({"success": True, "msg": f"连接成功！当前共有 {channel_count} 个活跃通道。"})
    except redis.exceptions.ConnectionError:
        return jsonify({"success": False, "msg": "未连通：无法连接到 Redis 服务器，请检查配置或服务是否已启动！"}), 500
    except Exception as e:
        return jsonify({"success": False, "msg": f"连接测试出错: {str(e)}"}), 500

@app.route('/api/redis/sync_all', methods=['POST'])
def api_redis_sync_all():
    try:
        op_redis.ping_server(db=0)
    except Exception as e:
        return jsonify({"success": False, "msg": f"无法连通 Redis 服务器，同步中止！原因: {str(e)}"}), 500
        
    configs = get_configs({})
    success_count = 0
    try:
        for c in configs:
            cid = c['config_id']
            content_str = c['content']
            op_redis.set_json(cid, content_str, db=0)
            success_count += 1
            
        return jsonify({"success": True, "msg": f"成功将 {success_count} 个配置项更新到 Redis。"}), 200
    except Exception as e:
        return jsonify({"success": False, "msg": f"操作 Redis 时出错: {str(e)}"}), 500

@app.route('/api/redis/check_all', methods=['GET'])
def api_redis_check_all():
    try:
        op_redis.ping_server(db=0)
    except Exception as e:
        return jsonify({"success": False, "msg": f"未连通 Redis 服务器，无法检查同步状态。原因: {str(e)}"}), 500

    configs = get_configs({})
    results = []
    try:
        for c in configs:
            cid = c['config_id']
            try:
                in_redis = op_redis.check_exists(cid, db=0)
            except:
                in_redis = False
            c['in_redis'] = in_redis
            results.append(c)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500

@app.route('/api/redis/sync_single/<config_id>', methods=['POST'])
def api_redis_sync_single(config_id):
    try:
        op_redis.ping_server(db=0)
    except Exception as e:
        return jsonify({"success": False, "msg": f"未连通 Redis 服务器，无法单独更新。原因: {str(e)}"}), 500

    local_data = get_config_by_id(config_id)
    if not local_data:
        return jsonify({"success": False, "msg": "本地不存在该配置项"}), 404
        
    try:
        op_redis.set_json(config_id, local_data['content'], db=0)
        return jsonify({"success": True, "msg": f"{config_id} 已单独更新同步至 Redis。"}), 200
    except Exception as e:
        return jsonify({"success": False, "msg": f"操作 Redis 时出错: {str(e)}"}), 500

@app.route('/api/redis/compare/<config_id>', methods=['GET'])
def api_redis_compare(config_id):
    try:
        op_redis.ping_server(db=0)
    except Exception as e:
        return jsonify({"success": False, "msg": f"未连通 Redis 服务器。原因: {str(e)}"}), 500

    local_data = get_config_by_id(config_id)
    if not local_data:
        return jsonify({"success": False, "msg": "本地未找到该配置项"}), 404
        
    try:
        local_json = json.loads(local_data['content'])
    except:
        local_json = {"value": local_data['content']}
        
    try:
        redis_data = op_redis.get_json(config_id, db=0)
    except:
        redis_data = None
        
    return jsonify({
        "success": True, 
        "local": local_json, 
        "redis": redis_data,
        "desc": local_data.get('description', ''),
        "param_desc": local_data.get('param_desc', '')
    })

@app.route('/api/mysql/get_config', methods=['GET'])
def api_mysql_get_config():
    config = get_config_by_id('SSTK0000')
    if not config:
        return jsonify({"success": False, "msg": "未找到 SSTK0000 配置项"}), 400
    try:
        content_json = json.loads(config['content'])
        stock_main = content_json.get('stock-main')
        if not stock_main:
            return jsonify({"success": False, "msg": "SSTK0000 中没有名为 'stock-main' 的项"}), 400
        return jsonify({"success": True, "data": stock_main})
    except json.JSONDecodeError:
        return jsonify({"success": False, "msg": "SSTK0000 的内容不是合法的JSON格式"}), 400

@app.route('/api/mysql/test_connection', methods=['POST'])
def api_mysql_test_connection():
    data = request.json
    try:
        host = data.get('host', '127.0.0.1')
        port = int(data.get('port', 3306))
        user = data.get('user', 'root')
        password = data.get('password', '')
        database = data.get('database', '')
        
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, connect_timeout=3)
        conn.close()
        return jsonify({"success": True, "msg": f"连接 MySQL 服务器 ({host}:{port}) 成功！"})
    except pymysql.MySQLError as e:
        return jsonify({"success": False, "msg": f"连接 MySQL 失败：{str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "msg": f"连接测试出错: {str(e)}"}), 500

@app.route('/api/pgsql/pool_list', methods=['GET'])
def api_pgsql_pool_list():
    configs = get_configs({})
    matches = []
    
    for c in configs:
        cid = c['config_id']
        if cid >= 'SSTKP000' and cid <= 'SSTKP999':
            is_valid = False
            stock_private = None
            try:
                content_json = json.loads(c['content'])
                stock_private = content_json.get('stock-private')
                if stock_private:
                    is_valid = True
            except:
                pass
            
            matches.append({
                "config_id": cid,
                "description": c['description'],
                "is_valid": is_valid,
                "config_data": stock_private
            })
            
    if not matches:
        return jsonify({"success": False, "msg": "未找到从 SSTKP000 到 SSTKP999 范围内的配置项！"}), 400
        
    return jsonify({"success": True, "data": matches})

@app.route('/api/pgsql/test_connection', methods=['POST'])
def api_pgsql_test_connection():
    data = request.json
    try:
        host = data.get('host', '127.0.0.1')
        port = int(data.get('port', 5432))
        user = data.get('user', 'postgres')
        password = data.get('password', '')
        database = data.get('database', '')
        
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database, connect_timeout=3)
        conn.close()
        return jsonify({"success": True, "msg": f"连接 PostgreSQL 服务器 ({host}:{port}) 成功！"})
    except psycopg2.Error as e:
        return jsonify({"success": False, "msg": f"连接 PostgreSQL 失败：{str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "msg": f"连接测试出错: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
