# FIXME: this should all be confirmed against what a DTD says
# (probably in a test; this may not match the DTD exactly, but we
# should document just how it differs).

# Data taken from http://www.w3.org/TR/html401/index/elements.html

empty_tags = [
    'area', 'base', 'basefont', 'br', 'col', 'frame', 'hr',
    'img', 'input', 'isindex', 'link', 'meta', 'param']

deprecated_tags = [
    'applet', 'basefont', 'center', 'dir', 'font', 'isindex',
    'menu', 's', 'strike', 'u']

# archive actually takes a space-separated list of URIs
link_attrs = [
    'action', 'archive', 'background', 'cite', 'classid',
    'codebase', 'data', 'href', 'longdesc', 'profile', 'src',
    'usemap',
    # Not standard:
    'dynsrc', 'lowsrc',
    ]

# Not in the HTML 4 spec:
# onerror, onresize
event_attrs = [
    'onblur', 'onchange', 'onclick', 'ondblclick', 'onerror',
    'onfocus', 'onkeydown', 'onkeypress', 'onkeyup', 'onload',
    'onmousedown', 'onmousemove', 'onmouseout', 'onmouseover',
    'onmouseup', 'onreset', 'onresize', 'onselect', 'onsubmit',
    'onunload',
    ]

safe_attrs = [
    'abbr', 'accept', 'accept-charset', 'accesskey', 'action', 'align',
    'alt', 'axis', 'border', 'cellpadding', 'cellspacing', 'char', 'charoff',
    'charset', 'checked', 'cite', 'class', 'clear', 'cols', 'colspan',
    'color', 'compact', 'coords', 'datetime', 'dir', 'disabled', 'enctype',
    'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace', 'id',
    'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
    'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
    'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape',
    'size', 'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title',
    'type', 'usemap', 'valign', 'value', 'vspace', 'width']

# From http://htmlhelp.com/reference/html40/olist.html
top_level_tags = [
    'html', 'head', 'body', 'frameset',
    ]

head_tags = [
    'base', 'isindex', 'link', 'meta', 'script', 'style', 'title',
    ]

general_block_tags = [
    'address',
    'blockquote',
    'center',
    'del',
    'div',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'ins',
    'isindex',
    'noscript',
    'p',
    'pre',
    ]

list_tags = [
    'dir', 'dl', 'dt', 'dd', 'li', 'menu', 'ol', 'ul',
    ]

table_tags = [
    'table', 'caption', 'colgroup', 'col',
    'thead', 'tfoot', 'tbody', 'tr', 'td', 'th',
    ]

# just this one from
# http://www.georgehernandez.com/h/XComputers/HTML/2BlockLevel.htm
block_tags = general_block_tags + list_tags + table_tags + [
    # Partial form tags
    'fieldset', 'form', 'legend', 'optgroup', 'option',
    ]

form_tags = [
    'form', 'button', 'fieldset', 'legend', 'input', 'label',
    'select', 'optgroup', 'option', 'textarea',
    ]

special_inline_tags = [
    'a', 'applet', 'basefont', 'bdo', 'br', 'embed', 'font', 'iframe',
    'img', 'map', 'area', 'object', 'param', 'q', 'script',
    'span', 'sub', 'sup',
    ]

phrase_tags = [
    'abbr', 'acronym', 'cite', 'code', 'del', 'dfn', 'em',
    'ins', 'kbd', 'samp', 'strong', 'var',
    ]

font_style_tags = [
    'b', 'big', 'i', 's', 'small', 'strike', 'tt', 'u',
    ]

frame_tags = [
    'frameset', 'frame', 'noframes',
    ]

# These tags aren't standard
nonstandard_tags = ['blink', 'marque']

tags = (top_level_tags + head_tags + general_block_tags + list_tags
        + table_tags + form_tags + special_inline_tags + phrase_tags
        + font_style_tags + nonstandard_tags)
