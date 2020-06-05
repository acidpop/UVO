#-*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options

from datetime import datetime
from time import sleep
import os
import sys
import pymysql
import sqlite3
import logging
import traceback
import telepot
import configparser

from LogManager import log

# User Information
mysql_use = False
sqlite_use = False

kia_id = ''
kia_pw = ''
mysql_id = ''
mysql_pw = ''
mysql_db = ''
mysql_host = ''
sqlite_db_path = ''
bot_token = ''
bot_chat_id = 0

def exception_hook(exc_type, exc_value, exc_traceback):
    log.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    log.info('Exception Hook End\n\n')


def GetConfig():
    try:
        global kia_id
        global kia_pw
        global mysql_id
        global mysql_pw
        global mysql_db
        global mysql_host
        global sqlite_db_path
        global bot_token
        global bot_chat_id
        config = configparser.ConfigParser()
        config.read('/home/pi/source/UVO/config.ini')
        mysql_use = config.getboolean('SETTING', 'USE_MYSQL') 
        sqlite_use = config.getboolean('SETTING', 'USE_SQLITE') 
        kia_id = config['KIA']['id']
        kia_pw = config['KIA']['pw']
        mysql_id = config['MYSQL']['id']
        mysql_pw = config['MYSQL']['pw']
        mysql_db = config['MYSQL']['db']
        mysql_host = config['MYSQL']['host']
        sqlite_db_path = config['SQLITE']['file_path']
        bot_token = config['BOT']['token']
        bot_chat_id = int(config['BOT']['chat_id'])
    except:
        msg = 'Get Config file except'
        log.error(msg)
        sys.excepthook = exception_hook


def GetUVOInfo(try_cnt):
    err_log = ''
    try:
        drv_path = '/usr/lib/chromium-browser/chromedriver'
        login_url = 'https://red.kia.com/kr/view/qlgi/login/qlgi_login.do'
        distance_url = 'https://red.kia.com/kr/kmgt/autoCareLinkInfo.do?scrnId=5053&screenNm=autoCareLinkInfo&paramType=ENS&paramVal=scrnId=5053'
        driven_info_url = 'https://red.kia.com/kr/kmgt/autoCareLinkInfo.do?scrnId=5056&screenNm=autoCareLinkInfo&paramType=ENS&paramVal=scrnId=5056'

        log.info("Get UVO Information Start")

        web_options = Options()
        web_options.add_argument('--headless')
        driver = webdriver.Chrome(drv_path, options=web_options)

        driver.get(login_url)

        # Version 1
        #driver.find_element_by_id('inetMbrId').send_keys(kia_id)
        #driver.find_element_by_id('pw').send_keys(kia_pw)

        #driver.execute_script("javascript:checkLogin(document.loginForm);")

        # Version 2 (2019-12-30)

        err_log = 'try Login'

        driver.find_element_by_xpath("//input[@type='email']").send_keys(kia_id)
        driver.find_element_by_xpath("//input[@type='password']").send_keys(kia_pw)

        driver.find_element_by_xpath("//button[@type='button']").click()
        # Version 2 End

        log.info("UVO Login Success")

        err_log = 'get distance url'

        driver.get(distance_url)

        log.info("UVO Get Distance URL success")

        sleep(60)
        driver.implicitly_wait(60)

        err_log = 'get distance iframe'

        driver.switch_to.frame(driver.find_element_by_id("H_IFRAME"))

        # #cont-article > div > p > span > b.orange
        niro_km = driver.find_element_by_css_selector("#cont-article > div > p > span > b.orange")

        accumulated_distance = niro_km.text.strip('km')

        # 운행 정보 출력
        err_log = 'get driven info url'
        driver.get(driven_info_url)

        log.info("UVO Get Driven information success")

        sleep(60)
        driver.implicitly_wait(60)

        driver.switch_to.frame(driver.find_element_by_id("H_IFRAME"))

        driver.switch_to.frame(driver.find_element_by_id("inner"))

        distance_driven = driver.find_element_by_css_selector("#dataList > tbody > tr:nth-child(3) > th:nth-child(2)")
        operating_time = driver.find_element_by_css_selector("#dataList > tbody > tr:nth-child(3) > th:nth-child(3)")
        average_speed = driver.find_element_by_css_selector("#dataList > tbody > tr:nth-child(3) > th:nth-child(4)")
        max_speed = driver.find_element_by_css_selector("#dataList > tbody > tr:nth-child(3) > th:nth-child(5)")
        safe_score = driver.find_element_by_css_selector("#dataList > tbody > tr:nth-child(3) > th:nth-child(6)")

        distance_driven_min = distance_driven.text
        distance_driven_min = distance_driven_min.replace(',', '')

        log.info("누적 거리 : %s", accumulated_distance)
        log.info("운행 거리 : %s", distance_driven_min)
        log.info("운행 시간 : %s", operating_time.text)
        log.info("평균 속도 : %s", average_speed.text)
        log.info("최고 속도 : %s", max_speed.text)
        log.info("안전 점수 : %s", safe_score.text)

        accumulated_distance = accumulated_distance.replace(',', '')

        data = (accumulated_distance, distance_driven_min, operating_time.text, average_speed.text, max_speed.text, safe_score.text)

        driver.quit()

        return True, data, err_log
        #return True, {'accumulated_distance' : accumulated_distance, 'distance_driven' : distance_driven.text, 'operating_time' : operating_time.text, 'average_speed' : average_speed.text, 'max_speed' : max_speed.text, 'safe_score' : safe_score.text}
    except:
        msg = "UVO 정보 가져오기 실패, Retry [%d/10]" % (try_cnt)
        log.error(msg)
        sys.excepthook = exception_hook
        driver.quit()
        return False, {}, err_log


def InsertSqliteDB(data):
    if sqlite_use == False:
        return

    conn = sqlite3.connect(sqlite_db_path)

    try:
        cur = conn.cursor()

        # Create Table
        query = "CREATE TABLE IF NOT EXISTS niro_data( date text, accumulated_distance integer, distance_driven integer, operating_time integer, average_speed integer, max_speed integer, safe_score real);"
        cur.execute(query)

        today = datetime.now().strftime("%Y/%m/%d")

        # query = "insert into niro_data(date, accumulated_distance, distance_driven, operating_time, average_speed, max_speed, safe_score) values (?, ?, ?, ?, ?, ?, ?);"
        #query = "insert into niro_data values (%s, %s, %s, %s, %s, %s, %s);" % (today, data['accumulated_distance'], data['distance_driven'], data['operating_time'], data['average_speed'], data['max_speed'], data['safe_score'])
        query = "insert into niro_data values (%s, %s, %s, %s, %s, %s, %s);" % (today, data[0], data[1], data[2], data[3], data[4], data[5])

        log.info("sqlite query : %s", query)

        cur.execute(query)
        conn.commit()
    except:
        log.error("Sqlite insert except")
        sys.excepthook = exception_hook
    finally:
        conn.close()

# Kia UVO 데이터 DB 테이블
"""
CREATE TABLE `niro_data` (
  `date` date NOT NULL COMMENT '측정 일자',
  `accumulated_distance` int(11) NOT NULL COMMENT '누적 거리(km)',
  `distance_driven` int(11) NOT NULL COMMENT '주행 거리(km)',
  `operating_time` int(11) NOT NULL COMMENT '운행 시간(m)',
  `average_speed` double DEFAULT NULL,
  `max_speed` int(11) NOT NULL COMMENT '최고 속도',
  `safe_score` double NOT NULL COMMENT '안전 점수(0~100)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Niro 운행 데이터';
"""

def InsertMySql(data):
    if mysql_use == False:
        return

    # Mysql Insert
    conn = pymysql.connect(host=mysql_host, user=mysql_id, password=mysql_pw, db=mysql_db, charset='utf8')
    curs = conn.cursor()

    #query = "insert into niro_data values(now(), %s, %s, %s, %s, %s, %s);" % (accumulated_distance, distance_driven.text, operating_time.text, average_speed.text, max_speed.text, safe_score.text)
    query = "insert into niro_data values(now(), %s, %s, %s, %s, %s, %s);" % ( data[0], data[1], data[2], data[3], data[4], data[5] )

    log.info("Mysql Query : %s", query)

    try:
        curs.execute(query)
        conn.commit()
    except:
        log.error("Mysql Insert Fail")
        sys.excepthook = exception_hook
    finally:
        conn.close()


# UVO 정보 성공 여부 DB 테이블
"""
CREATE TABLE `momsdiary_check` (
  `write_date` date NOT NULL COMMENT '작성일자',
  `writer` varchar(20) NOT NULL COMMENT '작성자',
  `is_success` int(1) NOT NULL COMMENT '작성여부'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Moms Diary Checker';
"""
def InsertDBSuccessResult():
    if mysql_use == False:
        return

    conn = pymysql.connect(host=mysql_host, user=mysql_id, password=mysql_pw, charset='utf8mb4', db=mysql_db)
    if( conn == None ):
        log.error('DB Connect Fail')
        return

    try:
        cur = conn.cursor()
        sql = "INSERT INTO `momsdiary_check` (`write_date`, `writer`, `is_success`) VALUES (CURRENT_DATE(), 'uvo', '1');"
        cur.execute(sql)
    except Exception as e:
        log.error(e)

    finally:
        conn.commit()
        cur.close()
        conn.close()


def main():
    isSucc = False
    retry_cnt = 10
    try_cnt = 1

    GetConfig()

    bot = telepot.Bot(bot_token)

    while isSucc == False and retry_cnt > 0:
        isSucc, data, errLog = GetUVOInfo(try_cnt)
        if isSucc:
            InsertSqliteDB(data)
            InsertMySql(data)
            log.info("Get UVO Information Succes, [%d/10]", try_cnt)
            bot.sendMessage(bot_chat_id, "UVO 정보 가져오기 성공")
            InsertDBSuccessResult()
            break
        else:
            log.info("Get UVO Information Fail, [%d/10]", try_cnt)
            if try_cnt == 10:
                msg = "UVO 정보 가져오기 실패\n[%s]\n, [%d/10]" % (errLog, try_cnt)
                bot.sendMessage(bot_chat_id, msg)

        retry_cnt = retry_cnt - 1
        try_cnt = try_cnt + 1

if __name__ == "__main__":
    main()

