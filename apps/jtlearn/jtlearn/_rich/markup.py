def escape(s):
    import re
    return re.sub(r"(\\*)(\[[A-Za-z#@/][^\[\]]*\])", lambda m: m.group(1) + "\\" + m.group(2), str(s))
