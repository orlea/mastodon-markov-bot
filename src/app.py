#!/usr/bin/env python3
import configparser
import time
import threading
import mastodonTool
import os
import datetime
import markovify
import exportModel
import re

# 環境変数の読み込み
config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')


def worker():
    # 学習
    domain = config_ini['read']['domain']
    read_access_token = config_ini['read']['access_token']
    write_access_token = config_ini['write']['access_token']
    override_acct = ''
    override_visibility = ''
    override_dryrun = False
    if 'override' in config_ini:
        if 'acct' in config_ini['override']:
            override_acct = config_ini['override']['acct']
        if 'visibility' in config_ini['override']:
            override_visibility = config_ini['override']['visibility']
        if 'dryrun' in config_ini['override']:
            override_dryrun = config_ini['override']['dryrun'] == "true"
        if 'remove_tags' in config_ini['override']:
            override_remove_tags = config_ini['override']['remove_tags']


    account_info = mastodonTool.get_account_info(domain, read_access_token, override_acct)
    params = {"exclude_replies": 1, "exclude_reblogs": 1}
    filename = "{}@{}".format(account_info["username"], domain)
    filepath = os.path.join("./chainfiles", os.path.basename(filename.lower()) + ".json")
    if (os.path.isfile(filepath) and datetime.datetime.now().timestamp() - os.path.getmtime(filepath) < 60 * 60 * 24):
        print("モデルは再生成されません")
    else:
        exportModel.generateAndExport(mastodonTool.loadMastodonAPI(domain, read_access_token, account_info['id'], params), filepath)
        print("LOG,GENMODEL," + str(datetime.datetime.now()) + "," + account_info["username"].lower())   # Log
    # 生成
    with open("./chainfiles/{}@{}.json".format(account_info["username"].lower(), domain)) as f:
        textModel = markovify.Text.from_json(f.read())
        sentence = textModel.make_sentence(tries=300)
        # botがbot以外のハッシュタグを汚染する事がある為取り除けるように
        if override_remove_tags != '':
            sentence = sentence.replace('#', '＃')
        sentence = "".join(sentence.split()) + ' #bot'
        sentence = re.sub(r'(:.*?:)', r' \1 ', sentence)
        print(sentence)
    try:
        body = {"status": sentence}
        if not override_dryrun:
            if override_visibility != '':
                body['visibility'] = override_visibility
            mastodonTool.post_toot(domain, write_access_token, body)
    except Exception as e:
        print("投稿エラー: {}".format(e))


def schedule(f, interval=1200, wait=True):
    base_time = time.time()
    next_time = 0
    while True:
        t = threading.Thread(target=f)
        t.start()
        if wait:
            t.join()
        next_time = ((base_time - time.time()) % interval) or interval
        time.sleep(next_time)


if __name__ == "__main__":
    # 定期実行部分
    schedule(worker)
    # worker()
