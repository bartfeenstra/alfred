from contracts import contract
from subprocess import call


_dmx_values = {
    'red': 0,
    'green': 0,
    'blue': 0,
    'luminosity': 0,
}


@contract()
def dmx_get_values() -> dict:
    global _dmx_values
    return _dmx_values


@contract
def dmx_set_values(red: int, green: int, blue: int, luminosity: int) -> dict:
    # This assumes:
    # - 4 identical lights.
    # - 7 channels per light (R, G, B, *, *, *, luminosity).
    # - Universe 1.
    # - The first light's address is 0.
    # - All lights occupy a continuous range of addresses.
    global _dmx_values
    _dmx_values['red'] = red
    _dmx_values['green'] = green
    _dmx_values['blue'] = blue
    _dmx_values['luminosity'] = luminosity
    ola_dmx_values = '%s,%s,%s,0,0,0,%s' % (red, green, blue, luminosity)
    print(['ola_set_dmx', '-u', '1', '-d', ola_dmx_values])
    call(['ola_set_dmx', '-u', '1', '-d', ola_dmx_values])
    return _dmx_values


# Reset the lights.
# @todo Does this execute every single time the module is included?
dmx_set_values(_dmx_values['red'], _dmx_values['green'], _dmx_values['blue'],
               _dmx_values['luminosity'])
