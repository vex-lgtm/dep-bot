import os
import json
import requests
from flask import Flask, request
from datetime import datetime, date, timedelta

app = Flask(__name__)

TOKEN = "9250820267:AAErExx52zd2jOGPbPKabYgSOu7hpMrlQ1w"
CHAT_ID = "1337412492"
STATS_FILE = "stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "today_deps": 0, "today_sum": 0.0,
        "total_deps": 0, "total_sum": 0.0,
        "last_reset": str(date.today()),
        "cabs": {}, "creos": {}, "statuses": {}, "dolets": 0,
        "campaigns": {}, "offers": {},
        "last_dep_time": None,
        "cab_history": {}
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
            [{"text": "Кампании"}, {"text": "Офферы"}],
            [{"text": "Кабинеты"}, {"text": "Крео"}],
            [{"text": "Отчёт"}, {"text": "Очистить"}]
        ],
        "resize_keyboard": True
    }

def reset_if_new_day():
    today = str(date.today())
    if stats.get("last_reset") != today:
        stats["today_deps"] = 0
        stats["today_sum"] = 0.0
        stats["last_reset"] = today
        save_stats(stats)

def check_alerts():
    now = datetime.now()
    # Алерт: нет депов больше часа
    last = stats.get("last_dep_time")
    if last:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt > timedelta(hours=1):
            send_message("⚠️ <b>Алерт:</b> Уже больше часа нет ни одного депа!")
            stats["last_dep_time"] = now.isoformat()  # чтобы не спамил
            save_stats(stats)

def full_stats_text():
    reset_if_new_day()
    msg = f"""📊 <b>Полная статистика</b>

📅 Сегодня: <b>{stats['today_deps']}</b> / <b>{stats['today_sum']:.2f}</b>
📈 Всего: <b>{stats['total_deps']}</b> / <b>{stats['total_sum']:.2f}</b>
✈️ Долетов: {stats.get('dolets', 0)}

<b>Кампании:</b>
"""
    for camp, data in sorted(stats.get("campaigns", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:10]:
        msg += f"• {camp}: {data['count']} / {data['sum']:.2f}\n"
    
    msg += "\n<b>Офферы:</b>\n"
    for off, data in sorted(stats.get("offers", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:10]:
        msg += f"• {off}: {data['count']} / {data['sum']:.2f}\n"
    
    return msg

@app.route('/postback', methods=['GET', 'POST'])
def postback():
    reset_if_new_day()
    check_alerts()
    
    data = request.args.to_dict()
    if request.is_json:
        data.update(request.json or {})
    
    subid = data.get('subid', '—')
    revenue = data.get('revenue', data.get('payout', '0'))
    status = data.get('status', 'sale').lower()
    cabinet = data.get('cabinet', data.get('ad_campaign_id', data.get('sub1', '—')))
    creo = data.get('creo', data.get('creative_id', data.get('sub2', '—')))
    offer = data.get('offer', data.get('offer_name', '—'))
    campaign = data.get('campaign', data.get('campaign_name', '—'))
    dolet = data.get('dolet', '0')
    
    try:
        rev = float(revenue)
    except:
        rev = 0.0
    
    # Обновляем время последнего депа
    stats["last_dep_time"] = datetime.now().isoformat()
    
    stats["today_deps"] += 1
    stats["today_sum"] += rev
    stats["total_deps"] += 1
    stats["total_sum"] += rev
    
    # Кампании
    if campaign not in stats["campaigns"]:
        stats["campaigns"][campaign] = {"count": 0, "sum": 0.0}
    stats["campaigns"][campaign]["count"] += 1
    stats["campaigns"][campaign]["sum"] += rev
    
    # Офферы
    if offer not in stats["offers"]:
        stats["offers"][offer] = {"count": 0, "sum": 0.0}
    stats["offers"][offer]["count"] += 1
    stats["offers"][offer]["sum"] += rev
    
    # Кабинеты + проверка на просадку
    if cabinet not in stats["cabs"]:
        stats["cabs"][cabinet] = {"count": 0, "sum": 0.0}
    old_count = stats["cabs"][cabinet]["count"]
    stats["cabs"][cabinet]["count"] += 1
    stats["cabs"][cabinet]["sum"] += rev
    
    # Простая проверка просадки (если раньше было много, а сейчас мало)
    if cabinet not in stats["cab_history"]:
        stats["cab_history"][cabinet] = []
    stats["cab_history"][cabinet].append(stats["cabs"][cabinet]["count"])
    if len(stats["cab_history"][cabinet]) > 5:
        recent = stats["cab_history"][cabinet][-3:]
        older = stats["cab_history"][cabinet][-6:-3]
        if older and sum(older) > 5 and sum(recent) < sum(older) * 0.4:
            send_message(f"⚠️ <b>Алерт:</b> Кабинет <b>{cabinet}</b> резко просел!")
    
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
    
    status_emoji = {"sale": "💰", "deposit": "💰", "dep": "💰", "lead": "📝", "registration": "📋"}.get(status, "📌")
    
    text = f"""{status_emoji} <b>Новый {status.upper()}!</b>

💵 Сумма депа: <b>{revenue}</b>
🏢 Кампания: <b>{campaign}</b>
🎯 Оффер: <b>{offer}</b>
📊 Кабинет: <b>{cabinet}</b>
🎨 Крео: <b>{creo}</b>
🆔 SubID: <code>{subid}</code>

📅 Сегодня: {stats['today_deps']} / {stats['today_sum']:.2f}
"""
    
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
        send_message("Бот запущен!", get_keyboard())
    
    elif text in ['/stats', 'Статистика', 'Отчёт', '/report']:
        send_message(full_stats_text(), get_keyboard())
    
    elif text in ['Кампании', '/campaigns']:
        msg = "🏢 <b>По кампаниям:</b>\n\n"
        for camp, data in sorted(stats.get("campaigns", {}).items(), key=lambda x: x[1]["sum"], reverse=True):
            msg += f"<b>{camp}</b>: {data['count']} / {data['sum']:.2f}\n"
        send_message(msg or "Пока пусто", get_keyboard())
    
    elif text in ['Офферы', '/offers']:
        msg = "🎯 <b>По офферам:</b>\n\n"
        for off, data in sorted(stats.get("offers", {}).items(), key=lambda x: x[1]["sum"], reverse=True):
            msg += f"<b>{off}</b>: {data['count']} / {data['sum']:.2f}\n"
        send_message(msg or "Пока пусто", get_keyboard())
    
    elif text in ['Кабинеты', '/cabs']:
        msg = "📊 <b>По кабинетам:</b>\n\n"
        for cab, data in sorted(stats.get("cabs", {}).items(), key=lambda x: x[1]["sum"], reverse=True):
            msg += f"<b>{cab}</b>: {data['count']} / {data['sum']:.2f}\n"
        send_message(msg or "Пока пусто", get_keyboard())
    
    elif text in ['Крео', '/creos']:
        msg = "🎨 <b>По крео:</b>\n\n"
        for creo, data in sorted(stats.get("creos", {}).items(), key=lambda x: x[1]["sum"], reverse=True)[:15]:
            msg += f"<b>{creo}</b>: {data['count']} / {data['sum']:.2f}\n"
        send_message(msg or "Пока пусто", get_keyboard())
    
    elif text in ['Очистить', '/clear']:
        new_stats = load_stats()
        new_stats["cabs"] = {}
        new_stats["creos"] = {}
        new_stats["campaigns"] = {}
        new_stats["offers"] = {}
        new_stats["statuses"] = {}
        new_stats["cab_history"] = {}
        new_stats["last_dep_time"] = None
        save_stats(new_stats)
        global stats
        stats = new_stats
        send_message("✅ Статистика очищена", get_keyboard())
    
    return "ok"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
