#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path

OLD_IPS = [
    '106.55.60.178', '38.175.203.40', '27.25.159.141', '1.94.96.71',
    '103.85.85.176', '111.180.197.115', '49.235.187.128', '180.188.19.128',
    '111.231.68.61',
]
OLD_PASSWORDS = [
    'long1251374638', 'qq258308277', 'wd.yuanmaba.vip', 'zhaolei520'
]
SKIP_SUFFIXES = {
    '.zip', '.7z', '.rar', '.pak', '.so', '.a', '.o', '.png', '.jpg', '.jpeg',
    '.gif', '.mp3', '.mp4', '.avi', '.dat', '.bin', '.luac', '.apk'
}


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    try:
        data = path.read_bytes()[:4096]
    except OSError:
        return False
    if b'\x00' in data:
        return False
    return True


def replace_text(root: Path, public_ip: str, mysql_password: str) -> None:
    bases = [root / 'home', root / 'www']
    for base in bases:
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if not path.is_file() or not is_probably_text(path):
                continue
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            new = text
            for old in OLD_IPS:
                new = new.replace(old, public_ip)
            for old in OLD_PASSWORDS:
                new = new.replace(old, mysql_password)

            # Keep DB connections local for host-network web/game containers.
            new = re.sub(r'(mysql_connect\(\s*["\'])[^"\']+(:3306["\'])', r'\g<1>127.0.0.1\2', new)
            new = re.sub(r'(define\(\s*["\']DBHOST["\']\s*,\s*["\'])[^"\']+(["\']\s*\))', r'\g<1>127.0.0.1\2', new)
            new = re.sub(r'(\$DBHOST\s*=\s*["\'])[^"\']+(["\'])', r'\g<1>127.0.0.1\2', new)
            new = re.sub(r'(\$host\s*=\s*["\'])[^"\']+(["\']\s*;\s*//代理后台数据库地址)', r'\g<1>127.0.0.1\2', new)
            new = re.sub(r'(\$host1\s*=\s*["\'])[^"\']+(["\']\s*;\s*//玩家账号数据库地址)', r'\g<1>127.0.0.1\2', new)
            if path.suffix.lower() == '.ini':
                new = re.sub(r'(?m)^(Host\s*=\s*).*$', r'\g<1>127.0.0.1', new)
            new = re.sub(r'(\\?"Host\\?"\s*:\s*\\?")[^"\\]+(\\?")', r'\g<1>127.0.0.1\2', new)

            # Normalize common PHP password assignments without touching unrelated secrets.
            new = re.sub(r'(\$DBPASS\s*=\s*)(["\']).*?\2', lambda m: f'{m.group(1)}"{mysql_password}"', new)
            new = re.sub(r'(\$pwd\s*=\s*)(["\']).*?\2(\s*;\s*//代理后台数据库密码)', lambda m: f'{m.group(1)}"{mysql_password}"{m.group(3)}', new)
            new = re.sub(r'(\$pwd1\s*=\s*)(["\']).*?\2(\s*;\s*//玩家账号数据库密码)', lambda m: f'{m.group(1)}"{mysql_password}"{m.group(3)}', new)
            new = re.sub(r'(Password\s*=).*', lambda m: f'{m.group(1)}{mysql_password}', new)
            new = re.sub(r'(\\?"Password\\?"\s*:\s*\\?")[^"\\]+(\\?")', lambda m: f'{m.group(1)}{mysql_password}{m.group(2)}', new)

            if new != text:
                path.write_text(new)


def remove_named_block(text: str, kind: str, name: str) -> str:
    m = re.search(r'\b' + re.escape(kind) + r'\s+' + re.escape(name) + r'\b', text)
    if not m:
        return text
    brace = text.find('{', m.end())
    if brace == -1:
        return text
    depth = 0
    in_s = in_d = False
    esc = False
    i = brace
    while i < len(text):
        ch = text[i]
        if esc:
            esc = False
        elif ch == '\\' and (in_s or in_d):
            esc = True
        elif ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    j = i + 1
                    while j < len(text) and text[j] in ' \t\r\n':
                        j += 1
                    return text[:m.start()].rstrip() + '\n\n' + text[j:].lstrip()
        i += 1
    return text


def remove_backdoors(root: Path) -> None:
    daili = root / 'www/wwwroot/daili'
    for rel in ['admin/sent_gids.php', 'includes/lang/class.upload.ja_JP.php']:
        p = daili / rel
        if p.exists():
            p.unlink()
            print(f'[INFO] removed backdoor file: {p}')
    func = daili / 'includes/function.php'
    if func.exists():
        text = func.read_text(errors='ignore')
        new = remove_named_block(text, 'function', 'handle_secure_request')
        new = remove_named_block(new, 'class', 'CallableClass')
        if new != text:
            func.write_text(new)
            print(f'[INFO] removed backdoor function/class: {func}')


def openssl_des(args, payload: bytes) -> bytes:
    cmd = ['openssl', 'enc'] + args + ['-provider', 'legacy', '-provider', 'default', '-K', b'548711fd'.hex()]
    p = subprocess.run(cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode(errors='ignore'))
    return p.stdout


def rewrite_sdk_json(root: Path, public_ip: str) -> None:
    path = root / 'www/wwwroot/zc/wd/110001_config_20190415.json'
    if not path.exists():
        print(f'[WARN] SDK JSON not found: {path}')
        return
    try:
        data = json.loads(path.read_text())
        cipher = bytes.fromhex(data['SdkConfig'])
    except Exception as exc:
        print(f'[WARN] cannot parse SDK JSON: {exc}')
        return
    try:
        plain_padded = openssl_des(['-des-ecb', '-d', '-nopad'], cipher)
    except Exception as exc:
        print(f'[WARN] cannot decrypt SDK JSON: {exc}')
        return
    end = plain_padded.rfind(b'}')
    if end < 0:
        print('[WARN] decrypted SDK config has no JSON end brace')
        return
    plain = plain_padded[:end + 1].decode('utf-8', errors='ignore')
    new_plain = plain
    for old in OLD_IPS:
        new_plain = new_plain.replace(old, public_ip)
    # Also normalize URL hosts while preserving original paths.
    new_plain = re.sub(r'http://[^/"\\]+:81', f'http://{public_ip}:81', new_plain)
    new_plain = re.sub(r'http://[^/"\\]+(?=/)', f'http://{public_ip}:81', new_plain)
    if new_plain == plain:
        print('[INFO] SDK JSON already matches target IP')
        return
    payload = new_plain.encode('utf-8')
    pad_len = 8 - (len(payload) % 8)
    payload += bytes([pad_len]) * pad_len
    try:
        new_cipher = openssl_des(['-des-ecb', '-e', '-nopad'], payload)
    except Exception as exc:
        print(f'[WARN] cannot encrypt SDK JSON: {exc}')
        return
    data['SdkConfig'] = new_cipher.hex()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f'[INFO] rewrote encrypted SDK JSON: {path}')


def report_remaining(root: Path) -> None:
    hits = []
    for base in [root / 'home', root / 'www']:
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if not path.is_file() or not is_probably_text(path):
                continue
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            if '/log/' in str(path):
                continue
            for old in OLD_IPS:
                if old in text:
                    hits.append(f'{path}: {old}')
                    break
            if len(hits) >= 50:
                break
    if hits:
        print('[WARN] remaining old-IP hits:')
        for hit in hits[:50]:
            print('  ' + hit)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: rewrite_config.py /path/to/rootfs', file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    public_ip = os.environ.get('PUBLIC_IP', '').strip()
    mysql_password = os.environ.get('MYSQL_ROOT_PASSWORD', 'long1251374638')
    remove_flag = os.environ.get('REMOVE_BACKDOORS', '1') == '1'
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', public_ip):
        print(f'[ERROR] invalid PUBLIC_IP: {public_ip}', file=sys.stderr)
        return 1
    if not (root / 'home').exists() or not (root / 'www').exists():
        print(f'[ERROR] invalid rootfs: {root}', file=sys.stderr)
        return 1
    replace_text(root, public_ip, mysql_password)
    if remove_flag:
        remove_backdoors(root)
    else:
        print('[WARN] REMOVE_BACKDOORS=0, confirmed RCE backdoor is left in place')
    rewrite_sdk_json(root, public_ip)
    report_remaining(root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
