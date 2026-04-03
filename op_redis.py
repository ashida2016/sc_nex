import redis
import json
from db import get_config_by_id

def get_redis_info():
    db_config = get_config_by_id('SRDS0000')
    if not db_config:
        raise Exception("未找到 SRDS0000 配置项")
    
    try:
        content_json = json.loads(db_config['content'])
        redis_main = content_json.get('redis-main')
        if not redis_main:
            raise Exception("SRDS0000 中没有名为 'redis-main' 的项")
    except json.JSONDecodeError:
        raise Exception("SRDS0000 的内容不是合法的JSON格式")
        
    host = redis_main.get('host', '127.0.0.1')
    port = int(redis_main.get('port', 6379))
    decode_responses = redis_main.get('decode_responses', True)
    
    return host, port, decode_responses

def get_redis_client(db=0, host=None, port=None, decode_responses=None):
    if host is None or port is None:
        h, p, d = get_redis_info()
        host = host or h
        port = port or p
        decode_responses = d if decode_responses is None else decode_responses
        
    return redis.Redis(
        host=host, 
        port=port, 
        db=db, 
        decode_responses=decode_responses, 
        socket_timeout=3, 
        socket_connect_timeout=3
    )

def ping_server(host=None, port=None, db=0, decode_responses=None):
    r = get_redis_client(db=db, host=host, port=port, decode_responses=decode_responses)
    r.ping()
    return r

def get_channel_count(host=None, port=None, db=0):
    r = ping_server(host=host, port=port, db=db)
    channels = r.pubsub_channels()
    return len(channels)

def check_exists(cid, db=0):
    r = get_redis_client(db=db)
    return r.exists(cid) > 0

def set_json(cid, content_str, db=0):
    r = get_redis_client(db=db)
    try:
        json_obj = json.loads(content_str)
    except json.JSONDecodeError:
        json_obj = {"value": content_str}
    r.json().set(cid, '$', json_obj)

def get_json(cid, db=0):
    r = get_redis_client(db=db)
    try:
        return r.json().get(cid)
    except Exception:
        return None
