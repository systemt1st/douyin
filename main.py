#Github：https://github.com/systemt1st
import time
import datetime
import csv
import os
import schedule
import smtplib
import logging
from email.mime.text import MIMEText
from email.header import Header

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 配置日志（同时输出到控制台和文件）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log", encoding="utf-8")
    ]
)

# 全局变量，用于保存上一次提取的数据
last_data = None
# 全局的 driver 实例（后续会自动重启）
driver = None

# 要监控的页面 URL
url = "https://www.douyin.com/user/xxx"


def get_driver():
    """初始化并返回一个新的 ChromeDriver 实例"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver_instance = webdriver.Chrome(options=chrome_options)
    driver_instance.get(url)
    time.sleep(5)  # 初次加载等待
    logging.info("浏览器初始化成功。")
    return driver_instance


def send_email(changes, new_data):
    """
    当监控数据发生变化时，通过邮件通知目标邮箱。
    请将 sender、password 替换为你自己的 QQ 邮箱及授权码。
    """
    sender = "xxx@qq.com"  # 替换为你的 QQ 邮箱
    password = "xxx"  # 替换为你的授权码
    receiver = "xxx@qq.com"  # 接收通知的邮箱
    smtp_server = "smtp.qq.com"
    smtp_port = 465  # 使用 SSL

    subject = "监控数据更新提醒"
    content = "监控数据发生变化：\n" + "\n".join(changes) + "\n\n最新数据：\n" + str(new_data)

    message = MIMEText(content, "plain", "utf-8")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = sender
    message["To"] = receiver

    try:
        smtp_obj = smtplib.SMTP_SSL(smtp_server, smtp_port)
        smtp_obj.login(sender, password)
        smtp_obj.sendmail(sender, [receiver], message.as_string())
        smtp_obj.quit()
        logging.info("邮件发送成功。")
    except Exception as e:
        logging.error("邮件发送失败: %s", e)


def extract_data_bs(html):
    """
    使用 BeautifulSoup 解析 page_source 获取关注、粉丝、获赞、抖音号和 IP属地的数据。
    """
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    # 关注
    follow_div = soup.find("div", {"data-e2e": "user-info-follow"})
    data["关注"] = follow_div.find("div", class_="sCnO6dhe").get_text(strip=True) if follow_div and follow_div.find(
        "div", class_="sCnO6dhe") else None
    # 粉丝
    fans_div = soup.find("div", {"data-e2e": "user-info-fans"})
    data["粉丝"] = fans_div.find("div", class_="sCnO6dhe").get_text(strip=True) if fans_div and fans_div.find("div",
                                                                                                              class_="sCnO6dhe") else None
    # 获赞
    likes_div = soup.find("div", {"data-e2e": "user-info-like"})
    data["获赞"] = likes_div.find("div", class_="sCnO6dhe").get_text(strip=True) if likes_div and likes_div.find("div",
                                                                                                                 class_="sCnO6dhe") else None
    # 抖音号和 IP属地
    user_info_p = soup.find("p", class_="cOO9eQ6W")
    if user_info_p:
        spans = user_info_p.find_all("span")
        for span in spans:
            text = span.get_text(strip=True)
            if "抖音号：" in text:
                data["抖音号"] = text.split("抖音号：")[-1]
            if "IP属地：" in text:
                data["IP属地"] = text.split("IP属地：")[-1]
    else:
        data["抖音号"] = None
        data["IP属地"] = None

    return data


def extract_data_selenium(driver):
    """
    使用 Selenium 的 XPath 定位方式提取关注、粉丝、获赞、抖音号以及 IP属地的数据。
    """
    data = {}
    try:
        data["关注"] = driver.find_element(By.XPATH,
                                           "//div[@data-e2e='user-info-follow']//div[contains(@class, 'sCnO6dhe')]").text
    except Exception:
        data["关注"] = None
    try:
        data["粉丝"] = driver.find_element(By.XPATH,
                                           "//div[@data-e2e='user-info-fans']//div[contains(@class, 'sCnO6dhe')]").text
    except Exception:
        data["粉丝"] = None
    try:
        data["获赞"] = driver.find_element(By.XPATH,
                                           "//div[@data-e2e='user-info-like']//div[contains(@class, 'sCnO6dhe')]").text
    except Exception:
        data["获赞"] = None
    try:
        douyin_elem = driver.find_element(By.XPATH,
                                          "//p[contains(@class, 'cOO9eQ6W')]//span[contains(text(), '抖音号：')]")
        data["抖音号"] = douyin_elem.text.split("抖音号：")[-1]
    except Exception:
        data["抖音号"] = None
    try:
        ip_elem = driver.find_element(By.XPATH, "//p[contains(@class, 'cOO9eQ6W')]//span[contains(text(), 'IP属地：')]")
        data["IP属地"] = ip_elem.text.split("IP属地：")[-1]
    except Exception:
        data["IP属地"] = None

    return data


def monitor(driver):
    """
    定时监控任务：
      - 刷新页面、等待关键元素加载完成，
      - 分别使用 Selenium 与 BeautifulSoup 提取数据，
      - 将数据写入 CSV 文件，
      - 对比上一次数据变化，如有变化则发邮件提醒。
    """
    global last_data
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info("开始监控任务: %s", current_time)
    try:
        driver.refresh()
        # 显式等待关键元素加载完成
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-e2e='user-info-follow']")))

        html = driver.page_source

        data_selenium = extract_data_selenium(driver)
        data_bs = extract_data_bs(html)

        # 合并两种提取结果
        data_combined = {
            "时间": current_time,
            "关注_selenium": data_selenium.get("关注"),
            "粉丝_selenium": data_selenium.get("粉丝"),
            "获赞_selenium": data_selenium.get("获赞"),
            "抖音号_selenium": data_selenium.get("抖音号"),
            "IP属地_selenium": data_selenium.get("IP属地"),
            "关注_bs": data_bs.get("关注"),
            "粉丝_bs": data_bs.get("粉丝"),
            "获赞_bs": data_bs.get("获赞"),
            "抖音号_bs": data_bs.get("抖音号"),
            "IP属地_bs": data_bs.get("IP属地")
        }
        logging.info("监控数据: %s", data_combined)

        # 写入 CSV
        file_name = "monitor_log.csv"
        file_exists = os.path.isfile(file_name)
        fieldnames = [
            "时间", "关注_selenium", "粉丝_selenium", "获赞_selenium",
            "抖音号_selenium", "IP属地_selenium",
            "关注_bs", "粉丝_bs", "获赞_bs", "抖音号_bs", "IP属地_bs"
        ]
        with open(file_name, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data_combined)

        # 对比上一次数据
        if last_data is not None:
            changes = []
            for key in data_combined:
                if key == "时间":
                    continue
                if data_combined.get(key) != last_data.get(key):
                    changes.append(f"{key}: {last_data.get(key)} -> {data_combined.get(key)}")
            if changes:
                logging.info("检测到数据变化，发送邮件提醒。变化内容：%s", changes)
                send_email(changes, data_combined)
            else:
                logging.info("数据无变化。")
        else:
            logging.info("这是第一次监控，无历史数据比对。")
        last_data = data_combined.copy()
    except Exception as e:
        logging.error("监控任务出错: %s", e)


def safe_monitor():
    """
    包装 monitor 方法：如果监控任务出错，则重启浏览器以确保后续任务正常执行。
    """
    global driver
    try:
        monitor(driver)
    except Exception as e:
        logging.error("safe_monitor 捕获异常: %s", e)
        try:
            driver.quit()
        except Exception as ex:
            logging.error("退出 driver 时出错: %s", ex)
        # 重启浏览器
        logging.info("正在重启浏览器实例...")
        driver = get_driver()


def main():
    global driver
    driver = get_driver()
    # 每隔 10 秒执行一次 safe_monitor
    schedule.every(10).seconds.do(safe_monitor)
    logging.info("开始定时监控...")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("定时监控已停止。")
    except Exception as e:
        logging.error("主循环异常: %s", e)
    finally:
        try:
            driver.quit()
        except Exception as e:
            logging.error("退出浏览器异常: %s", e)


if __name__ == "__main__":
    main()
