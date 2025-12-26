# python-cloud

一个基于 **Flask + SQLite** 的简易网盘系统，支持用户注册登录、文件上传下载、文件夹管理以及后台管理功能。  
适合作为 Flask 学习项目或个人轻量级文件管理工具。期末python作业

---

## ✨ 功能特性

- 👤 用户注册 / 登录
- 📁 文件夹创建、重命名、删除
- ⬆️ 文件上传 / ⬇️ 下载
- 🗂 文件列表展示[
- 🔐 管理员后台]()
- 💾 SQLite 本地数据库

---

## 📦 项目结构

```text
pythonProject/
├─ app/
│  ├─ routes/        # 路由（auth / admin / file / folder）
│  ├─ templates/     # 模板文件
│  ├─ static/        # 静态资源
│  ├─ models.py      # 数据模型
│  ├─ utils.py       # 工具函数
│  └─ config.py      # 配置文件
├─ templates/        # 前台模板
├─ static/           # 前台静态资源
├─ uploads/          # 用户上传目录
├─ run.py            # 启动入口
├─ .gitignore
└─ README.md

```
---
## 如何使用
编译环境为 Python 3.12
```
run.py #运行该文件启动 默认端口为3000
```
