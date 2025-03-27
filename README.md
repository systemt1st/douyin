## 简介
本工具用于实时监控指定抖音用户主页数据变化，包括：关注数、粉丝数、获赞数、抖音号、IP属地等信息。当监控到数据发生变化时，会自动发送邮件通知，并记录到日志文件和CSV数据文件中，便于后续分析与统计。

## 功能特点
- **实时数据监控**：每10秒钟自动抓取抖音个人主页的数据。
- **自动通知**：数据发生变化时，自动发送邮件提醒。
- **多种数据抓取方式**：结合使用 Selenium 和 BeautifulSoup 两种方式提取数据，确保准确性与可靠性。
- **数据持久化**：记录数据到CSV文件中，便于后续数据分析。
- **日志记录**：详细记录监控过程中的运行状态与错误信息。

## 依赖环境
- Python 3.7+
- Selenium
- BeautifulSoup
- schedule
- smtplib
- ChromeDriver

## 使用方法
### 环境搭建
```bash
pip install selenium beautifulsoup4 schedule

配置
在send_email函数中替换以下信息为你自己的邮箱与授权码：

python
始终显示详情

复制
sender = "你的QQ邮箱"
password = "你的邮箱授权码"
receiver = "接收通知的邮箱"
运行
执行以下命令启动监控工具：

bash
始终显示详情

复制
python monitor.py
监控过程中的数据会保存在monitor_log.csv文件中，日志信息记录在monitor.log中。

注意事项
确保ChromeDriver版本与本地Chrome浏览器版本相匹配。

定期检查运行日志，及时处理可能发生的异常情况。

避免过于频繁的请求，以防止账号或IP被封禁。
