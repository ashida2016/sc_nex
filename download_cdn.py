import urllib.request
import os
import re

files = {
    'css/bootstrap.min.css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css',
    'css/datatables.min.css': 'https://cdn.datatables.net/v/bs5/jq-3.7.0/dt-2.0.8/r-3.0.2/datatables.min.css',
    'js/bootstrap.bundle.min.js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
    'js/datatables.min.js': 'https://cdn.datatables.net/v/bs5/jq-3.7.0/dt-2.0.8/r-3.0.2/datatables.min.js',
    'js/echarts.min.js': 'https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js',
    'css/all.min.css': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
}

os.makedirs('d:/src_github_qq/sc_nex/static/css', exist_ok=True)
os.makedirs('d:/src_github_qq/sc_nex/static/js', exist_ok=True)
os.makedirs('d:/src_github_qq/sc_nex/static/webfonts', exist_ok=True)

for path, url in files.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = response.read()
            # If it's the fontawesome CSS, we should find all webfonts and download them too
            if path == 'css/all.min.css':
                css_text = data.decode('utf-8')
                urls = re.findall(r'url\((.*?)\)', css_text)
                for w_url in set(urls):
                    w_path = w_url.strip('"\'')
                    if w_path.startswith('../webfonts/'):
                        font_filename = w_path.split('?')[0].split('#')[0].replace('../webfonts/', '')
                        font_url = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/{font_filename}"
                        try:
                            req_f = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req_f) as res_f:
                                w_data = res_f.read()
                                with open(f'd:/src_github_qq/sc_nex/static/webfonts/{font_filename}', 'wb') as f_out:
                                    f_out.write(w_data)
                                print(f"Downloaded font: {font_filename}")
                        except Exception as e_f:
                            print(f"Failed to download font {font_url}: {e_f}")
            
            with open('d:/src_github_qq/sc_nex/static/' + path, 'wb') as out_file:
                out_file.write(data)
            print(f"Downloaded {path}")
    except Exception as e:
        print(f"Failed to download {path}: {e}")
