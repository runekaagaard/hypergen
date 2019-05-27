import string


def base65_counter():
    BS = string.letters + string.digits + "-_:"
    b = len(BS)
    i = -1
    while True:
        i += 1
        s = i
        res = ""
        while s:
            res += BS[s % b]
            s //= b
        res = res[::-1] or "a"
        try:
            int(res[0])
            yield "h" + res
        except ValueError:
            yield res


c = base65_counter()
for i in range(100):
    print next(c),
