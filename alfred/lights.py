from subprocess import call

_dmx_values = {
    'color': '#abcdef',
    'luminosity': 0,
}


def dmx_get_values() -> dict:
    global _dmx_values
    return _dmx_values


def dmx_set_values(color: str, luminosity: int) -> dict:
    # This assumes:
    # - 4 identical lights.
    # - 7 channels per light (R, G, B, *, *, *, luminosity).
    # - Universe 1.
    # - The first light's address is 0.
    # - All lights occupy a continuous range of addresses.
    global _dmx_values
    _dmx_values = {
        'color': color,
        'luminosity': luminosity,
    }
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    ola_dmx_values = ','.join(
        ['%s,%s,%s,0,0,0,%s' % (red, green, blue, luminosity)] * 4)
    call(['ola_set_dmx', '-u', '1', '-d', ola_dmx_values])
    return _dmx_values


# Reset the lights.
# @todo Does this execute every single time the module is included?
# dmx_set_values(_dmx_values['color'], _dmx_values['luminosity'])
