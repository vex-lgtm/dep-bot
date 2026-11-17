import os
import requests
from flask import Flask, request
from datetime import datetime, date

app = Flask(__name__)

TOKEN = "9250820267:AAErExx52zd2jOGPbPKabYgSOu7hpMrlQ1w"
CHAT_ID = "1337412492"

# Статистика
stats = {
    "today_deps": 0,
    "today_sum": 0,
    "total_deps": 0,
    "total_sum": 0,
    "last_reset": str(date.today())
}

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })

def reset_if_new_day():
    today = str(date.today())
    if stats["last_reset"] != today:
        stats["today_deps"] = 0
        stats["today_sum"] = 0
        stats["last_reset"] = today

@app.route('/postback', methods=['GET', 'POST'])
def postback():
    reset_if_new_day()
    
    data = request.args.to_dict()
    if request.is_json:
        data.update(request.json or {})
    
    subid = data.get('subid', data.get('sub_id', '—'))
    revenue = data.get('revenue', data.get('payout', data.get('sum', '0')))
    status = data.get('status', 'sale')
    cabinet = data.get('cabinet', data.get('cab', data.get('sub1', '—')))
    creo = data.get('creo', data.get('creative', data.get('sub2', '—')))
    offer = data.get('offer', data.get('offer_name', '—'))
    
    try:
        rev = float(revenue)
    except:
        rev = 0
    
    stats["today_deps"] += 1
    stats["today_sum"] += rev
    stats["total_deps"] += 1
    stats["total_sum"] += rev
    
    text = f"""💰 <b>Новый деп!</b>

💵 Сумма: <b>{revenue}</b>
📊 Кабинет: <b>{cabinet}</b>
🎨 Крео: <b>{creo}</b>
🎯 Оффер: {offer}
🆔 SubID: <code>{subid}</code>
📌 Статус: {status}

📅 Сегодня: {stats['today_deps']} депов / {stats['today_sum']:.2f}
"""
    
    send_message(text)
    return "ok"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    if 'message' not in update:
        return "ok"
    
    chat_id = update['message']['chat']['id']
    text = update['message'].get('text', '')
    
    if str(chat_id) != str(CHAT_ID):
        return "ok"
    
    reset_if_new_day()
    
    if text == '/start':
        send_message("Бот запущен!\n\nКоманды:\n/today — статистика за сегодня\n/stats — общая статистика\n/help — помощь")
    
    elif text == '/today':
        msg = f"""📅 <b>Сегодня</b>

Депов: <b>{stats['today_deps']}</b>
Сумма: <b>{stats['today_sum']:.2f}</b>
"""
        send_message(msg)
    
    elif text == '/stats':
        msg = f"""📊 <b>Общая статистика</b>

Всего депов: <b>{stats['total_deps']}</b>
Общая сумма: <b>{stats['total_sum']:.2f}</b>

Сегодня: {stats['today_deps']} / {stats['today_sum']:.2f}
"""
        send_message(msg)
    
    elif text == '/help':
        send_message("Команды:\n/today — сегодня\n/stats — всё время")
    
    return "ok"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
