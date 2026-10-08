import asyncio, os, re, socket
from datetime import date
import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton as IB, InlineKeyboardMarkup as IM, KeyboardButton as KB, Message, ReplyKeyboardMarkup)
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv
load_dotenv()
API, STOKEN = os.getenv('API_URL'), os.getenv('BOT_SERVICE_TOKEN')
router = Router(); users = {}  # telegram_id -> role (keshda)

class ChiqimState(StatesGroup):
    dori = State(); partiya = State(); miqdor = State(); sabab = State(); izoh = State(); tasdiq = State()
class LinkState(StatesGroup): kod = State()
class NomState(StatesGroup): q = State()

async def api(method, path, tg, **kw):
    """Barcha chaqiruvlar async, timeout=10. (status, json) yoki (None, None) qaytaradi."""
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
            r = await c.request(method, API + path, headers={'X-Bot-Token': STOKEN, 'X-Telegram-Id': str(tg)}, **kw)
            return r.status_code, r.json()
    except (httpx.HTTPError, ValueError):
        return None, None

async def role_of(tg):
    if tg in users: return users[tg]
    s, d = await api('GET', '/auth/me/', tg)
    if s == 200: users[tg] = d['role']; return d['role']

def menu(role):
    rows = [[KB(text='Qoldiq (shtrix kod)'), KB(text='Chiqim qilish')], [KB(text='Muddati tugayotganlar')]]
    if role == 'admin': rows.append([KB(text='Kirim'), KB(text='Hisobot')])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def days_left(s): return (date.fromisoformat(s) - date.today()).days
def line(b):
    k = days_left(b['yaroqlilik_sanasi'])
    flag = ' MUDDATI O\'TGAN' if k < 0 else (' вљ пёЏ' if k < 30 else '')
    return f"{flag} {b['partiya_raqami']}: {float(b['qoldiq']):g}, {b['sotuv_narxi']} so'm, {b['yaroqlilik_sanasi']} ({k} kun)"

# ---- bog'lash ----
@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    r = await role_of(m.from_user.id)
    if r: return await m.answer('Xush kelibsiz!', reply_markup=menu(r))
    await state.set_state(LinkState.kod); await m.answer("Administrator veb-paneldan bergan bog'lash kodini yuboring:")
@router.message(LinkState.kod)
async def link(m: Message, state: FSMContext):
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
            r = await c.post(API + '/bot/link/', headers={'X-Bot-Token': STOKEN}, json={'code': m.text.strip(), 'telegram_id': m.from_user.id})
    except httpx.HTTPError: return await m.answer('Server javob bermayapti, birozdan keyin urinib koring')
    if r.status_code != 200: return await m.answer(r.json().get('detail', 'Xato'))
    users[m.from_user.id] = r.json()['role']; await state.clear()
    await m.answer('Akkaunt ulandi.', reply_markup=menu(r.json()['role']))
@router.message(Command('bekor'))
async def bekor(m: Message, state: FSMContext): await state.clear(); await m.answer('Bekor qilindi.')

# ---- shtrix kod ----
async def show_barcode(m: Message, code, tg=None):
    s, d = await api('GET', f'/medicines/barcode/{code}/', tg or m.from_user.id)
    if s is None: return await m.answer('Server javob bermayapti, birozdan keyin urinib koring')
    if s == 404: return await m.answer("Bunday shtrix kod bazada yo'q. Administratorga murojaat qiling", reply_markup=IM(inline_keyboard=[[IB(text='Nom boyicha qidirish', callback_data='nom')]]))
    txt = f"{d['name']}\n{d['manufacturer']}\nUmumiy qoldiq: {float(d['qoldiq']):g} {d['unit']}\n\n" + '\n'.join(line(b) for b in d['partiyalar'] if float(b['qoldiq']) > 0 or days_left(b['yaroqlilik_sanasi']) < 0)
    await m.answer(txt, reply_markup=IM(inline_keyboard=[[IB(text='Chiqim qilish', callback_data=f"cq:{d['id']}"), IB(text='Yopish', callback_data='yop')]]))
@router.callback_query(F.data == 'yop')
async def yop(c: CallbackQuery): await c.message.delete()

# ---- muddati tugayotganlar ----
@router.message(F.text == 'Muddati tugayotganlar')
async def exp_menu(m: Message):
    if not await role_of(m.from_user.id): return await m.answer('Avval /start')
    await m.answer('Muddat oralig\'i:', reply_markup=IM(inline_keyboard=[[IB(text=f'{d} kun', callback_data=f'exp:{d}:1') for d in (7, 30, 90)]]))
@router.callback_query(F.data.startswith('exp:'))
async def exp_list(c: CallbackQuery):
    p = c.data.split(':'); days, page = p[1], int(p[2]) if len(p) > 2 else 1
    s, d = await api('GET', f'/stock/expiring/?days={days}&page_size=200', c.from_user.id)
    if s is None: return await c.answer('Server javob bermayapti', show_alert=True)
    rows = d['results']
    if not rows: return await c.message.answer(f"Yaqin {days} kunda muddati tugaydigan dori yo'q")
    part = rows[(page - 1) * 10: page * 10]
    nav = ([IB(text='Oldingi', callback_data=f'exp:{days}:{page-1}')] if page > 1 else []) + ([IB(text='Keyingi', callback_data=f'exp:{days}:{page+1}')] if page * 10 < len(rows) else [])
    await c.message.answer('\n'.join(f"{b['dori_nomi']} | {line(b)}" for b in part), reply_markup=IM(inline_keyboard=[nav]) if nav else None); await c.answer()

# ---- chiqim FSM ----
@router.message(Command('chiqim'))
@router.message(F.text == 'Chiqim qilish')
async def ch0(m: Message, state: FSMContext):
    if not await role_of(m.from_user.id): return await m.answer('Avval /start')
    await state.set_state(ChiqimState.dori); await m.answer("Dori shtrix kodi yoki nomining bir qismini yuboring (/bekor)")
@router.callback_query(F.data.startswith('cq:'))
async def ch_from_card(c: CallbackQuery, state: FSMContext): await pick_medicine(c, state, c.data[3:])
async def pick_medicine(c, state, mid):
    s, d = await api('GET', f'/batches/?medicine={mid}&page_size=100', c.from_user.id)
    rows = [b for b in (d or {}).get('results', []) if float(b['qoldiq']) > 0]
    if not rows: return await c.message.answer("Qoldig'i bor partiya yo'q"); 
    await state.set_state(ChiqimState.partiya)
    await c.message.answer('Partiyani tanlang (muddati yaqini birinchi):', reply_markup=IM(inline_keyboard=[[IB(text=f"{b['partiya_raqami']} | {float(b['qoldiq']):g} | {b['yaroqlilik_sanasi']}", callback_data=f"cb:{b['id']}:{b['qoldiq']}:{b['sotuv_narxi']}")] for b in rows])); await c.answer()
@router.message(ChiqimState.dori)
async def ch1(m: Message, state: FSMContext):
    s, d = await api('GET', f'/medicines/?search={m.text.strip()}', m.from_user.id)
    if s is None: return await m.answer('Server javob bermayapti, birozdan keyin urinib koring')
    if not d['results']: return await m.answer('Topilmadi, qayta yuboring')
    await m.answer('Natijalar:', reply_markup=IM(inline_keyboard=[[IB(text=x['name'], callback_data=f"cq:{x['id']}")] for x in d['results'][:8]]))
@router.callback_query(ChiqimState.partiya, F.data.startswith('cb:'))
async def ch2(c: CallbackQuery, state: FSMContext):
    _, bid, q, price = c.data.split(':'); await state.update_data(partiya=int(bid), qoldiq=float(q))
    await state.set_state(ChiqimState.miqdor); await c.message.answer(f"Miqdorni yuboring (qoldiq: {float(q):g})"); await c.answer()
@router.message(ChiqimState.miqdor)
async def ch3(m: Message, state: FSMContext):
    try: v = float(m.text.replace(',', '.')); assert v > 0
    except Exception: return await m.answer('Musbat son yuboring')
    q = (await state.get_data())['qoldiq']
    if v > q: return await m.answer(f"Bu partiyada {q:g} bor, ko'proq yoza olmaysiz")
    await state.update_data(miqdor=v); await state.set_state(ChiqimState.sabab)
    await m.answer('Sabab:', reply_markup=IM(inline_keyboard=[[IB(text=t.capitalize(), callback_data=f'sb:{t}') for t in ('sotuv', 'qaytarish', 'yaroqsiz')]]))
@router.callback_query(ChiqimState.sabab, F.data.startswith('sb:'))
async def ch4(c: CallbackQuery, state: FSMContext):
    sabab = c.data[3:]; await state.update_data(sabab=sabab, izoh='')
    if sabab == 'yaroqsiz': await state.set_state(ChiqimState.izoh); await c.message.answer('Izoh yozing:')
    else: await confirm(c.message, state)
    await c.answer()
@router.message(ChiqimState.izoh)
async def ch_izoh(m: Message, state: FSMContext): await state.update_data(izoh=m.text); await confirm(m, state)
async def confirm(m, state):
    d = await state.get_data(); await state.set_state(ChiqimState.tasdiq)
    await m.answer(f"Partiya #{d['partiya']}, miqdor: {d['miqdor']:g}, sabab: {d['sabab']} {d['izoh']}", reply_markup=IM(inline_keyboard=[[IB(text='Tasdiqlash', callback_data='ok'), IB(text='Bekor qilish', callback_data='no')]]))
@router.callback_query(ChiqimState.tasdiq, F.data.in_({'ok', 'no'}))
async def ch_done(c: CallbackQuery, state: FSMContext):
    if c.data == 'no': await state.clear(); return await c.message.answer('Bekor qilindi')
    d = await state.get_data()
    s, r = await api('POST', '/stock-out/', c.from_user.id, json={'partiya': d['partiya'], 'miqdor': str(d['miqdor']), 'sabab': d['sabab'], 'izoh': d['izoh'], 'sana': date.today().isoformat()})
    if s is None: return await c.message.answer('Server javob bermayapti, birozdan keyin urinib koring')
    if s == 201: await state.clear(); return await c.message.answer(f"Chiqim yozildi. Yangi qoldiq: {float(r['yangi_qoldiq']):g}")
    await state.set_state(ChiqimState.miqdor); await c.message.answer(f"{r.get('detail')}\nMiqdorni qayta yuboring")

# ---- admin ----
@router.message(F.text == 'Hisobot')
async def hisobot(m: Message):
    if await role_of(m.from_user.id) != 'admin': return
    s, d = await api('GET', '/reports/summary/', m.from_user.id)
    if s == 200: await m.answer(f"Dorilar: {d['dorilar_soni']}\nOmbor qiymati: {d['ombor_qiymati']}\nMuddati yaqinlar: {d['muddati_yaqinlar']}")
@router.callback_query(F.data == 'chiqim')
async def cb_chiqim(c: CallbackQuery, state: FSMContext): await state.set_state(ChiqimState.dori); await c.message.answer('Dori nomi yoki shtrix kodi:'); await c.answer()

# ---- menyu tugmalari va nom bo'yicha qidirish ----
@router.message(F.text == 'Qoldiq (shtrix kod)')
async def qoldiq_btn(m: Message):
    if not await role_of(m.from_user.id): return await m.answer('Avval /start')
    await m.answer('Shtrix kodni raqamlar bilan yuboring (8-32 ta raqam)')
@router.message(F.text == 'Kirim')
async def kirim_btn(m: Message):
    if await role_of(m.from_user.id) != 'admin': return
    await m.answer('Kirimni hozircha veb-sahifa yoki admin panel orqali yozing')
@router.callback_query(F.data == 'nom')
async def nom_btn(c: CallbackQuery, state: FSMContext):
    await state.set_state(NomState.q); await c.message.answer('Dori nomining bir qismini yuboring (/bekor)'); await c.answer()
@router.message(NomState.q)
async def nom_q(m: Message, state: FSMContext):
    s, d = await api('GET', f'/medicines/?search={m.text.strip()}', m.from_user.id)
    if s is None: return await m.answer('Server javob bermayapti, birozdan keyin urinib koring')
    if not d['results']: return await m.answer('Topilmadi, qayta yuboring')
    await state.clear()
    await m.answer('Natijalar:', reply_markup=IM(inline_keyboard=[[IB(text=x['name'], callback_data=f"bc:{x['barcode']}")] for x in d['results'][:8]]))
@router.callback_query(F.data.startswith('bc:'))
async def bc_pick(c: CallbackQuery): await show_barcode(c.message, c.data[3:], c.from_user.id); await c.answer()

# ---- umumiy matn: shtrix kod ----
@router.message(F.text)
async def text(m: Message):
    if not await role_of(m.from_user.id): return await m.answer('Avval /start orqali akkauntni ulang')
    if re.fullmatch(r'\d{8,32}', m.text.strip()): return await show_barcode(m, m.text.strip())
    await m.answer("Bu shtrix kodga o'xshamaydi")

async def main():
    dp = Dispatcher(); dp.include_router(router)
    proxy = os.getenv('PROXY_URL')  # Telegram bloklangan bo'lsa .env ga yozing
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    await dp.start_polling(Bot(os.getenv('TELEGRAM_BOT_TOKEN'), session=session))
if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print('Bot to\'xtatildi')
