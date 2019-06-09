TEMPLATE = "### TEMPLATE-ELEMENT ###"
RENDERED = "### RENDERED-ELEMENTS ###"
TEMPLATE_VOID = "### TEMPLATE-VOID-ELEMENT ###"
RENDERED_VOID = "### RENDERED-VOID-ELEMENTS ###"

TAGS = [
    'a', 'abbr', 'address', 'article', 'aside', 'audio', 'b', 'bdi', 'bdo',
    'blockquote', 'body', 'button', 'canvas', 'caption', 'cite', 'code',
    'colgroup', 'datalist', 'dd', 'del_', 'details', 'dfn', 'dl', 'dt', 'em',
    'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'header', 'html', 'i', 'iframe', 'ins', 'kbd', 'keygen',
    'label', 'legend', 'li', 'main', 'map', 'mark', 'menu', 'meter', 'nav',
    'object', 'ol', 'optgroup', 'option', 'output', 'p', 'pre', 'progress',
    'q', 'rp', 'rt', 'ruby', 's', 'samp', 'section', 'select', 'small', 'span',
    'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'textarea',
    'tfoot', 'th', 'thead', 'time', 'tr', 'u', 'ul', 'var', 'video', 'script',
    'style', 'html', 'body', 'head'
]

VOID_TAGS = [
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'meta', 'param',
    'source', 'track', 'wbr', 'command', 'keygen', 'menuitem'
]

code = open("_hypergen.py").read()
template = code.split(TEMPLATE)[1]

s = ""
for tag in TAGS:
    s += template.replace("div", tag)

code = code.replace(RENDERED, s)

###

template = code.split(TEMPLATE_VOID)[1]
s = ""
for tag in VOID_TAGS:
    s += template.replace("link", tag)

code = code.replace(RENDERED_VOID, s)

open("hypergen.py", "w").write(code)
