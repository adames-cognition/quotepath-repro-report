"""Character-level analysis: why git octal-quoted paths break sorted-file-list consumers."""

def git_quote(name: str) -> str:
    out = []
    for ch in name:
        bs = ch.encode("utf-8")
        if len(bs) == 1 and bs[0] < 128:
            out.append(ch)
        else:
            out.extend(f"\\{b:03o}" for b in bs)
    return '"' + "".join(out) + '"'


name = "設計書_画面一覧.xlsx"
quoted = git_quote(name)
print("real name          :", name)
print("utf8 bytes (hex)   :", name.encode("utf-8").hex(" "))
print("git-quoted display :", quoted)
print("first char of quoted string:", repr(quoted[0]), "ASCII", ord(quoted[0]), hex(ord(quoted[0])))
print()
print("ASCII sort order: '!'=%d  '\"'=%d  '0'=%d  'A'=%d  'a'=%d" % (ord("!"), ord('"'), ord("0"), ord("A"), ord("a")))
print("=> any quoted path (leading 0x22) sorts BEFORE all alphanumeric names,")
print("   and AFTER only space(0x20) and !(0x21) -- hence the !OVERVIEW.md control works.")
print()
print("cluster-id fragment check ('343202' from warning 'cluster-...343202...xlsx-...'):")
for nm in ["設計書_画面一覧.xlsx", "テスト計画書.md", "メイン処理.py", "海上入出荷実績_設計書.md"]:
    octs = "".join(f"{b:03o}" for b in nm.encode("utf-8"))
    print(f"  {nm}: octal-concat contains '343202' = {'343202' in octs}")
    if "343202" in octs:
        idx = octs.index("343202")
        print(f"    at octal-digit offset {idx}; 343 202 = bytes 0xE3 0x82 (start of Japanese kana/UTF-8 lead)")
