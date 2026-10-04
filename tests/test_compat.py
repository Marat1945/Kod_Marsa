# -*- coding: utf-8 -*-
"""
Проверка совместимости ПК-версии с Android-версией «Код Марса».

Файл android_vectors.tsv получен запуском НАСТОЯЩЕГО кода из APK
(16.06.2025): там названия и HEX всех ключей, HEX ключ-фраз и шифровки,
сделанные телефонным кодом. Тест проверяет, что компьютер:
  * знает те же ключи в том же порядке;
  * получает тот же HEX из ключ-фразы;
  * расшифровывает шифровки телефона и выдаёт ту же морзянку.

Запуск:  python tests/test_compat.py
Экспорт шифровок ПК для обратной проверки телефонным кодом:
         python tests/test_compat.py --export pc_vectors.tsv
"""
import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import marscore as core  # noqa: E402


def unb64(s):
    return base64.b64decode(s).decode("utf-8")


def spec_key(spec):
    if spec.startswith("list:"):
        return core.key_bytes(int(spec[5:]))
    return core.phrase_key(unb64(spec[len("phrase:"):]))


def load():
    names, keys, vectors, phrases = None, {}, [], []
    with open(os.path.join(HERE, "android_vectors.tsv"), encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "NAMES":
                names = unb64(p[1]).split("|")
            elif p[0] == "KEY":
                keys[int(p[1])] = p[2]
            elif p[0] == "VEC":
                vectors.append(p[1:])
            elif p[0] == "PHRASEHEX":
                phrases.append((unb64(p[1]), p[2]))
    return names, keys, vectors, phrases


def main():
    names, keys, vectors, phrases = load()
    errors = []

    def check(ok, what):
        if not ok:
            errors.append(what)

    check(names == core.key_names(), "названия ключей не совпадают с телефоном")
    check(len(keys) == 32, "в эталоне должно быть 32 ключа")
    for i, h in keys.items():
        check(core.BUILTIN_KEYS[i][1] == h, f"HEX ключа №{i} не совпадает")
    for phrase, h in phrases:
        check(core.phrase_key(phrase).hex() == h, f"HEX ключ-фразы «{phrase}» не совпадает")

    for spec, plain_b64, cipher, morse in vectors:
        key, plain = spec_key(spec), unb64(plain_b64)
        check(core.decrypt(core.b32decode(cipher), key) == plain, f"не расшифрована шифровка телефона ({spec})")
        if morse != "-":
            check(core.to_morse(cipher) == morse, f"морзянка отличается от телефонной ({spec})")
            check(core.morse_to_b32(morse) == cipher, f"морзянка не переводится обратно ({spec})")
        mine = core.b32encode(core.encrypt(plain, key))
        check(core.decrypt(core.b32decode(mine), key) == plain, f"круг ПК→ПК не сошёлся ({spec})")

    # автоподбор: шифровка ключом «Код 31», выбран «Код 4»
    spec, plain_b64, cipher, _ = next(v for v in vectors if v[0] == "list:31")
    cands = [(core.key_bytes(4), "Код 4", True)] + [
        (core.key_bytes(i), core.BUILTIN_KEYS[i][0], False) for i in range(32)]
    text, label, primary = core.decrypt_any(core.b32decode(cipher), cands)
    check(text == unb64(plain_b64) and label == "Код 31" and not primary, "автоподбор ключа")

    # шифровка с пробелами и строчными буквами (как переписанная с бланка)
    spaced = " ".join(cipher[i:i + 5] for i in range(0, len(cipher), 5)).lower()
    check(core.decrypt(core.b32decode(spaced), spec_key(spec)) == unb64(plain_b64), "шифровка с пробелами")

    # QR туда и обратно
    for _, _, cipher, _ in vectors[:6]:
        check(core.read_qr(core.qr_image(core.qr_matrix(cipher), 4)) == [cipher], "QR не распознан")

    total = len(vectors)
    if errors:
        print("ОШИБКИ:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"OK: 32 ключа, {len(phrases)} ключ-фразы, {total} шифровок телефона расшифрованы, "
          f"морзянка совпадает, QR и автоподбор ключа работают.")

    if "--export" in sys.argv:
        out = sys.argv[sys.argv.index("--export") + 1]
        with open(out, "w", encoding="utf-8") as f:
            for spec, plain_b64, _, _ in vectors:
                cipher = core.b32encode(core.encrypt(unb64(plain_b64), spec_key(spec)))
                f.write(f"{spec}\t{plain_b64}\t{cipher}\n")
        print("шифровки ПК записаны в", out)


if __name__ == "__main__":
    main()
