<div align="center">

# 🖼️ **TIF 图像处理系统**

[![Flask](https://img.shields.io/badge/Flask-3.0.0-brightgreen?style=flat-square)](https://flask.palletsprojects.com/)
[![Vue](https://img.shields.io/badge/Vue.js-3.0-4FC08D?style=flat-square&logo=vue.js)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-latest-409EFF?style=flat-square&logo=element)](https://element-plus.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

_✨ 一个现代化的 TIF 图像批处理系统，支持智能孤立点检测和 IP 白名单管理 ✨_

</div>

---

## ✨ **功能特点**

### 🎯 核心功能

- 📤 **批量处理**：支持多个 TIF 文件的上传和处理  
- 🔍 **智能检测**：自动识别并处理图像中的孤立点  
- ⚙️ **参数配置**：可调节白色和黑色孤立点的阈值  
- 📦 **结果打包**：自动压缩处理结果并提供下载链接  

### 🛡️ 管理功能

- 🔐 **安全登录**：管理员账户系统  
- 🌐 **IP 控制**：白名单管理，精确控制访问权限  
- 🔑 **密码管理**：支持修改管理员密码  
- 📊 **系统设置**：可配置默认处理参数  

### 📋 任务队列管理

- 🔄 **多任务处理**：支持多个任务同时排队处理  
- 📊 **状态监控**：实时显示队列状态和等待位置  
- ⏱️ **顺序处理**：按照先来后到的顺序处理任务  
- 🔔 **实时更新**：支持任务状态实时更新和提醒  
- 📍 **来源追踪**：显示任务来源IP和创建时间  

---

## 🔨 **系统架构**

### 后端技术栈

- Flask (Python Web 框架)  
- PyJWT (认证)  
- PyMySQL (数据库)  
- OpenCV (图像处理)  
- NumPy & SciPy (科学计算)  

### 前端技术栈

- Vue.js 3  
- Element Plus UI  
- Axios  
- Vue Router  

---

## 🚀 **部署指南**

### 1️⃣ 数据库配置

#### 创建数据库和表结构：

```sql
-- 创建数据库
CREATE DATABASE ip_manager;

-- 创建管理员表
CREATE TABLE admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建 IP 白名单表
CREATE TABLE allowed_ips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建白名单设置表
CREATE TABLE whitelist_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建默认设置表
CREATE TABLE default_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    white_threshold INT DEFAULT 0,
    black_threshold INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 插入默认管理员账户
INSERT INTO admin_users (username, password) VALUES ('admin', 'admin123');
```

---

### 2️⃣ 后端部署

#### 步骤：

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置数据库连接（在 `app.py` 中）：
   ```python
   db_config = {
       'host': '127.0.0.1',
       'user': 'root',
       'password': 'your_password',
       'database': 'ip_manager',
       'charset': 'utf8mb4'
   }
   ```

3. 运行后端服务：
   ```bash
   python app.py
   ```

---

### 3️⃣ 前端部署

#### 步骤：

1. 安装依赖：
   ```bash
   cd vue/my-vue-app
   npm install
   ```

2. 配置 API 地址（在 `src/config/api.js` 中）：
   ```javascript
   export const API_BASE_URL = 'http://your_server_ip:5000';
   ```

3. 构建生产版本：
   ```bash
   npm run build
   ```

4. 部署到 Web 服务器：
   ```bash
   # 将 dist 目录下的文件复制到 Web 服务器目录
   cp -r dist/* /var/www/html/
   ```

---

## 📝 **使用说明**

1. **访问系统首页**：上传和处理 TIF 图像  
2. **管理员登录**：访问 `/admin/login`，登录后可管理 IP 白名单和系统设置  
3. **参数设置**：在处理页面调整孤立点阈值  
4. **结果下载**：处理完成后，下载压缩包  

---

## ⚠️ **注意事项**

- **文件权限**：确保上传文件夹和处理文件夹具有正确的读写权限  
- **数据备份**：定期备份数据库  
- **密码管理**：及时更新管理员密码  
- **白名单配置**：正确设置 IP 白名单以确保安全  
- **HTTPS 使用**：建议在生产环境中启用 HTTPS  

---

## 📜 **许可证**

本项目基于 [MIT License](LICENSE) 开源。

---

## 👤 **作者**

- **姓名**：Xiao Hei  
- **Email**：[597875010@qq.com](mailto:597875010@qq.com)  
- **博客**：[dogni.work](https://dogni.work)  