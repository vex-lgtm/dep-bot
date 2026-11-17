import os
import json
import requests
from flask import Flask, request
from datetime import datetime, date

app = Flask(__name__)

TOKEN = "9250820267:AAErExx52zd2jOGPbPKabYgSOu7hpMrlQ1w"
CHAT_ID = "1337412492"
STATS_FILE = "stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "today_deps": 0,
        "today_sum": 0.0,
        "total_deps": 0,
        "total_sum": 0.0,
        "last_reset": str(date.today()),
        "cabs": {},
        "creos": {},
        "statuses": {},
        "dolets": 0
    }

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

stats = load_stats()

def send_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, data=payload)

def get_keyboard():
    return {
        "keyboard": [
            [{"text": "Старт"}, {"text": "Статистика"}],
            [{"text": "Кабинеты"}, {"text": "Крео"}],
            [{"text": "Отчёт"}, {"text": "Очистить"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def reset_if_new_day():
    today = str(date.today())
    if stats.get("last_reset") != today:
        stats["today_deps"] = 0
        stats["today_sum"] = 0.0
        stats["last_reset"] = today
        save_stats(stats)

def full_stats_text():
    reset_if_new_day()
    msg = f"""📊 <b>Полная статистика</b>

📅 Сегодня: <b>{stats['today_deps']}</b> депов / <b>{stats['today_sum']:.2f}</b>
📈 Всего: <b>{stats['total_deps']}</b> / <b>{stats['total_sum']:.2f}</b>
✈️ Долетов: {stats.get('dolets', 0)}

<b>Статусы:</b>
"""
    for st, cnt in stats.get("statuses", {}).items():
        msg += f"• {st}: {cnt}\n"
    
    msg += "\n<b>Топ кабинетов:</b>\n"
    top_cabs = sorted(stats.get("cabs", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:10]
    for cab, data in top_cabs:
        msg += f"• {cab}: {data['count']} / {data['sum']:.2f}\n"
    if not top_cabs:
        msg += "Пока нет данных\n"
    
    msg += "\n<b>Топ крео:</b>\n"
    top_creos = sorted(stats.get("creos", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:10]
    for creo, data in top_creos:
        msg += f"• {creo}: {data['count']} / {data['sum']:.2f}\n"
    if not top_creos:
        msg += "Пока нет данных\n"
    
    return msg

@app.route('/postback', methods=['GET', 'POST'])
def postback():
    reset_if_new_day()
    
    data = request.args.to_dict()
    if request.is_json:
        data.update(request.json or {})
    
    subid = data.get('subid', data.get('sub_id', '—'))
    revenue = data.get('revenue', data.get('payout', data.get('sum', '0')))
    status = data.get('status', 'sale').lower()
    cabinet = data.get('cabinet', data.get('cab', data.get('ad_campaign_id', data.get('sub1', '—'))))
    creo = data.get('creo', data.get('creative', data.get('creative_id', data.get('sub2', '—'))))
    offer = data.get('offer', data.get('offer_name', '—'))
    dolet = data.get('dolet', data.get('arrival', '0'))
    
    try:
        rev = float(revenue)
    except:
        rev = 0.0
    
    stats["today_deps"] += 1
    stats["today_sum"] += rev
    stats["total_deps"] += 1
    stats["total_sum"] += rev
    
    if cabinet not in stats["cabs"]:
        stats["cabs"][cabinet] = {"count": 0, "sum": 0.0}
    stats["cabs"][cabinet]["count"] += 1
    stats["cabs"][cabinet]["sum"] += rev
    
    if creo not in stats["creos"]:
        stats["creos"][creo] = {"count": 0, "sum": 0.0}
    stats["creos"][creo]["count"] += 1
    stats["creos"][creo]["sum"] += rev
    
    if status not in stats["statuses"]:
        stats["statuses"][status] = 0
    stats["statuses"][status] += 1
    
    if dolet and str(dolet) not in ['0', '']:
        stats["dolets"] += 1
    
    save_stats(stats)
    
    status_emoji = {
        "sale": "💰", "deposit": "💰", "dep": "💰",
        "lead": "📝", "registration": "📋", "reg": "📋",
        "rejected": "❌", "trash": "🗑"
    }.get(status, "📌")
    
    text = f"""{status_emoji} <b>Новый {status.upper()}!</b>

💵 Сумма: <b>{revenue}</b>
📊 Кабинет: <b>{cabinet}</b>
🎨 Крео: <b>{creo}</b>
🎯 Оффер: {offer}
🆔 SubID: <code>{subid}</code>

📅 Сегодня: {stats['today_deps']} / {stats['today_sum']:.2f}
"""
    if dolet and str(dolet) not in ['0', '']:
        text += f"\n✈️ Долет: {dolet}"
    
    send_message(text)
    return "ok"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    if 'message' not in update:
        return "ok"
    
    chat_id = str(update['message']['chat']['id'])
    text = update['message'].get('text', '')
    
    if chat_id != CHAT_ID:
        return "ok"
    
    reset_if_new_day()
    
    if text in ['/start', 'Старт']:
        send_message("Бот запущен! Выбери действие:", get_keyboard())
    
    elif text in ['/stats', 'Статистика', '/today']:
        send_message(full_stats_text(), get_keyboard())
    
    elif text in ['/cabs', 'Кабинеты']:
        msg = "📊 <b>По кабинетам:</b>\n\n"
        for cab, data in sorted(stats.get("cabs", {}).items(), key=lambda x: x[1]["sum"], reverse=True):
            msg += f"<b>{cab}</b>: {data['count']} шт / {data['sum']:.2f}\n"
        if not stats.get("cabs"):
            msg += "Пока пусто"
        send_message(msg, get_keyboard())
    
    elif text in ['/creos', 'Крео']:
        msg = "🎨 <b>По крео:</b>\n\n"
        for creo, data in sorted(stats.get("creos", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:20]:
            msg += f"<b>{creo}</b>: {data['count']} шт / {data['sum']:.2f}\n"
        if not stats.get("creos"):
            msg += "Пока пусто"
        send_message(msg, get_keyboard())
    
    elif text in ['/report', 'Отчёт']:
        send_message(full_stats_text(), get_keyboard())
    
    elif text in ['/clear', 'Очистить']:
        stats.clear()
        stats.update({
            "today_deps": 0, "today_sum": 0.0,
            "total_deps": 0, "total_sum": 0.0,
            "last_reset": str(date.today()),
            "cabs": {}, "creos": {}, "statuses": {}, "dolets": 0
        })
        save_stats(stats)
        send_message("✅ Статистика очищена", get_keyboard())
    
    elif text == '/help':
        send_message("Используй кнопки внизу или команды:\n/start /stats /cabs /creos /report /clear", get_keyboard())
    
    return "ok"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
