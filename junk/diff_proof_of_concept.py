def the_page(sections):
    for section in sections:
        with skippable(), diffing(), caching(), hashing(
                section=section) as hashed, div_cm(class_="section"):
            p(hashed.section.title, height=hashed.section.height)


first_html, _ = hypergen(get_sections(), diffing=True, previous_html=None)

print first_html
{
    47109385: '<div class="section">Section1</p>',
    39582039: '<div class="section">Section2</p>',
    35203802: '<div class="section">Section3</p>',
}

# Fails if extends is called outside of a diffing context manager.
next_html, diff = hypergen(
    get_sections(), diffing=True, previous_html=first_html)

print next_html
{
    47109385: '<div class="section">Section1</p>',
    30948594: '<div class="section">Section4</p>',
    83592891: '<div class="section">Section5</p>',
}

print diff
(
    ('-', 39582039),
    ('-', 35203802),
    ('+', 30948594),
    ('+', 83592891), )
