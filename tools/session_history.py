#!/usr/bin/env python3
"""История разговоров ролей в читаемом виде: team/history/<роль>/<дата>_<id>.md.
Маскирует ключи, токены, пароли, номера карт, IP, хэши, значения из .env и строки из redact-hashes.txt (sha256).
Если файл секретов не читается — останавливается.
"""
import json, glob, os, re, sys
from datetime import datetime
PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Claude Code хранит журналы в папке, где все знаки кроме букв и цифр заменены на «-»
SRC = os.path.expanduser('~/.claude/projects/' + re.sub(r'[^A-Za-z0-9]', '-', PROJECT))
DST = os.path.join(PROJECT, 'team', 'history')

def clean(t):
    t = re.sub(r'[^A-Za-z0-9 ._-]', '', t or '').strip()
    return re.sub(r'\s+', '-', t) or 'other-sessions'


SECRET_PATTERNS = [
    (re.compile(r'\b(sk|pk|rk)[-_](live|test|proj|ant)?[-_]?[A-Za-z0-9_-]{16,}'), '[КЛЮЧ СКРЫТ]'),
    (re.compile(r'\b(ghp|gho|ghs|github_pat|xox[abpr]|AKIA|AIza)[A-Za-z0-9_-]{12,}'), '[КЛЮЧ СКРЫТ]'),
    (re.compile(r'\b\d{6,}:[A-Za-z0-9_-]{30,}'), '[КЛЮЧ СКРЫТ]'),
    (re.compile(r'(?i)\b(пароль|password|passwd|pwd|token|токен|secret|api[_ -]?key)((?:\s+(?:от|для|к|for|to)\s+[^:=—\n]{1,40}?)?\s*(?:[:=—–-]+\s*|\s+))(\S{4,})'), r'\1\2[СКРЫТО]'),
    (re.compile(r'(?i)\b([A-Z0-9_]*(PASSWORD|PASSWD|PASS|SECRET|TOKEN|API_?KEY)[A-Z0-9_]*)(\s*[:=]\s*)(`?)\S{4,}?\4(?=\s|$|[|,;])'), r'\1\3[СКРЫТО]'),
    (re.compile(r'(?i)(\|\s*(пароль|password|passwd|secret|token|токен|api[_ -]?key|ключ)[^|]{0,30}\|\s*)`?[^|`\s]{4,}`?'), r'\1[СКРЫТО]'),
    (re.compile(r'\b([a-z][a-z0-9+.-]*)://([^:\s/@]+):[^@\s]+@'), r'\1://\2:[СКРЫТО]@'),
    (re.compile(r'\b(?:\d[ -]?){13,19}\b'), lambda m: '[НОМЕР СКРЫТ]' if sum(c.isdigit() for c in m.group(0)) >= 13 else m.group(0)),
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b(?<!127\.0\.0\.1)'), '[IP СКРЫТ]'),
    (re.compile(r'\b[A-Fa-f0-9]{40,}\b'), lambda m: m.group(0)[:8] + '…'),
]

import hashlib
REDACT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'redact-hashes.txt')
REDACT = set()
if os.path.exists(REDACT_FILE):
    REDACT = {l.strip().lower() for l in open(REDACT_FILE) if re.fullmatch(r'[0-9a-fA-F]{64}', l.strip())}

ENV_FILES = [os.path.join(PROJECT, '.env')]  # файлы с секретами; значения ≥8 знаков маскируются
ENV_VALUES = []
for _ef in ENV_FILES:
    if not os.path.exists(_ef):
        continue  # файла секретов нет — маскировать нечего
    try:
        for _l in open(_ef, encoding='utf-8', errors='replace'):
            _l = _l.strip()
            if not _l or _l.startswith('#') or '=' not in _l:
                continue
            _v = _l.split('=', 1)[1].strip().strip('"').strip("'")
            if len(_v) >= 8:
                ENV_VALUES.append(_v)
    except OSError as _e:
        sys.exit(f'СТОП: не читается {_ef} ({_e.__class__.__name__}) — история без маски не собирается')
ENV_VALUES.sort(key=len, reverse=True)

def mask(t):
    for v in ENV_VALUES:
        if v in t:
            t = t.replace(v, '[СКРЫТО ИЗ .env]')
    for rx, rep in SECRET_PATTERNS:
        t = rx.sub(rep, t)
    if REDACT:
        t = re.sub(r'\S+', lambda m: '[СКРЫТО ПО СПИСКУ]' if hashlib.sha256(m.group(0).encode()).hexdigest() in REDACT else m.group(0), t)
    return t

def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for c in content or []:
        if not isinstance(c, dict):
            continue
        if c.get('type') == 'text':
            out.append(c.get('text', ''))
        elif c.get('type') == 'tool_use':
            inp = c.get('input') or {}
            d = inp.get('description') or inp.get('action_summary') or ''
            name = c.get('name', '')
            if 'send_message' in name:
                out.append(f"→ сообщение {inp.get('session_id','')[:14]}: {inp.get('message','')}")
            else:
                out.append(f"· [{name.split('__')[-1]}] {d}".rstrip())
    return '\n'.join(x for x in out if x)

def main():
    n = 0
    for f in sorted(glob.glob(f'{SRC}/*.jsonl')):
        title, lines, start = None, [], None
        seen = set()
        for raw in open(f, encoding='utf-8', errors='replace'):
            try:
                d = json.loads(raw)
            except Exception:
                continue
            if d.get('type') == 'custom-title':
                title = d.get('customTitle')
            if d.get('type') not in ('user', 'assistant') or d.get('isSidechain'):
                continue
            key = d.get('uuid') or (d.get('timestamp'), str((d.get('message') or {}).get('content'))[:200])
            if key in seen:
                continue
            seen.add(key)
            m = d.get('message') or {}
            c = m.get('content')
            if isinstance(c, list) and all(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
                continue
            t = text_of(c).strip()
            if not t:
                continue
            try:
                ts = datetime.fromisoformat(d.get('timestamp','').replace('Z','+00:00')).astimezone().strftime('%Y-%m-%d %H:%M')
            except Exception:
                ts = d.get('timestamp', '')[:16].replace('T', ' ')
            start = start or ts
            who = 'Роль' if d['type'] == 'assistant' else 'Входящее'
            if d['type'] == 'user' and 'cross-session-message' in t:
                mm = re.search(r'name="([^"]*)"', t)
                who = f"Сообщение от {mm.group(1) if mm else 'сессии'}"
                t = re.sub(r'</?cross-session-message[^>]*>', '', t)
                t = t.split('This came from another Claude session')[0].strip()
            elif d['type'] == 'user':
                who = 'Владелец или система'
            lines.append(f'**{ts} · {who}**\n\n{mask(t)}\n')
        if not lines:
            continue
        role = clean(title or 'без-названия')
        os.makedirs(f'{DST}/{role}', exist_ok=True)
        name = f"{start[:10]}_{start[11:16].replace(':','')}_{os.path.basename(f)[:8]}.md"
        with open(f'{DST}/{role}/{name}', 'w', encoding='utf-8') as o:
            o.write(f'# {mask(title or role)} — разговор с {start}\n\nИсточник: {os.path.basename(f)}\n\n' + '\n'.join(lines))
        n += 1
    print(f'файлов истории: {n} → {DST}')

if __name__ == '__main__':
    main()
