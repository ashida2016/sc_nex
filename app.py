from flask import Flask, render_template, request, jsonify
import json
import re
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
        
    success = add_config(config_id, category, abbr, seq, description, content_serialized)
    if success:
        return jsonify({"success": True, "msg": "添加成功"})
    else:
        return jsonify({"success": False, "msg": "添加失败，数据库错误"}), 500

@app.route('/api/config/<config_id>', methods=['PUT', 'DELETE'])
def api_edit_config(config_id):
    if request.method == 'PUT':
        data = request.json
        description = data.get('description', '')
        content_str = data.get('content', '')
        
        try:
            content_json = json.loads(content_str)
            content_serialized = json.dumps(content_json, ensure_ascii=False)
        except json.JSONDecodeError:
            return jsonify({"success": False, "msg": "配置项内容必须是合法的JSON格式！"}), 400
            
        success = update_config(config_id, description, content_serialized)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
