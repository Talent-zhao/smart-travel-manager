import pymysql

# 让 Django 使用 pymysql 替代 MySQLdb
pymysql.install_as_MySQLdb()

# 设置版本号，避免 Django 版本检查错误
pymysql.version_info = (1, 4, 6, "final", 0)

