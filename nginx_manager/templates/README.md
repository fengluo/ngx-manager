# Nginx 配置模板

本目录包含用于生成nginx配置的Jinja2模板文件。

## 模板文件

- `proxy_ssl.conf.j2` - HTTPS代理配置模板
- `static_ssl.conf.j2` - HTTPS静态文件配置模板  
- `proxy_http.conf.j2` - HTTP代理配置模板
- `static_http.conf.j2` - HTTP静态文件配置模板

## 使用方法

### 基本使用

```python
from nginx_manager.templates.generator import ConfigGenerator

# 创建生成器实例
gen = ConfigGenerator()

# 生成HTTPS代理配置
config = gen.generate_site_config(
    domain='api.example.com',
    backend='http://localhost:3000',
    ssl=True
)

# 生成HTTP静态文件配置
config = gen.generate_site_config(
    domain='static.example.com',
    ssl=False
)
```

### 使用自定义模板

```python
# 使用特定模板文件
config = gen.generate_site_config(
    domain='custom.example.com',
    backend='http://localhost:4000',
    template_name='custom_proxy.conf.j2'
)
```

### 查看可用模板

```python
# 列出所有可用模板
templates = gen.list_available_templates()
print(templates)

# 查看模板内容
content = gen.get_template_content('proxy_ssl.conf.j2')
print(content)
```

## 模板变量

模板中可以使用以下变量：

- `{{ domain }}` - 域名
- `{{ backend }}` - 后端服务地址 (仅代理模板)
- `{{ ssl }}` - 是否启用SSL
- `{{ ssl_cert_path }}` - SSL证书路径
- `{{ ssl_key_path }}` - SSL私钥路径
- `{{ access_log }}` - 访问日志路径
- `{{ error_log }}` - 错误日志路径

## 自定义模板

您可以在 `templates/` 目录中添加自己的模板文件：

1. 创建新的 `.j2` 文件
2. 使用上述模板变量
3. 遵循nginx配置语法
4. 通过 `template_name` 参数使用自定义模板

### 示例自定义模板

```nginx
# custom_proxy.conf.j2
server {
    listen 80;
    server_name {{ domain }};
    
    # 自定义配置
    client_max_body_size 100M;
    
    location / {
        proxy_pass {{ backend }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # 自定义代理配置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 自定义日志
    access_log {{ access_log }} combined;
    error_log {{ error_log }} warn;
}
```

## 注意事项

- 模板文件必须使用 `.j2` 扩展名
- 建议在修改模板后测试nginx配置语法
- SSL模板会自动添加HTTP到HTTPS重定向
- 所有模板都包含Let's Encrypt challenge支持 