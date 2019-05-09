# python-htmlgen
Fast (hopefully), pure python, parallizable, caching and diffing html generator. No more templates, just write python (or cython).

# High level Python api:

```python
@hgen
def my_page(sections):
    h1("My Page", _class="top-h1")
    for section in sections:
        with section_cm(height=100):
            div(section.content, style={"margin": auto})
```

# Caching context manager

```python
@hgen
def my_page(
    for section in sections:
        with section_cm(height=100), cache_cm(key=my_page, section=section) as data:
            div(data.content, style={"margin": auto})
```

# Low level Python api

```python
@hgen
def my_page(items):
    for item in items:
        o_div(_class="item") # Opens.
        write(item.text) # Writes verbatim.
        c_div() # Closes.
```

# Pure c Cython (nogil)

Does not touch python.

```cython
cdef string my_page(int n) nogil:
    hgen_start()
    cdef char i_str[10]

    o_ul_ng()
    for i in range(n):
        sprintf(i_str, <char*> "%d", k)

        li_ng(<char*> "My content.", [
            a(<char*> "class", <char*> "a-class"),
            a(<char*> "width", <char*> i_str),
            T # Terminates.
        ])
    c_ul_ng()

    return hgen_stop()
```
