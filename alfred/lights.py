from subprocess import call


def dmx_set_values(red, green, blue, luminosity):
    # This assumes:
    # - 4 identical lights.
    # - 7 channels per light (R, G, B, *, *, *, luminosity).
    # - Universe 1.
    # - The first light's address is 0.
    # - All lights occupy a continuous range of addresses.
    dmx_values = '%s,%s,%s,0,0,0,%s' % (red, green, blue, luminosity)
    print ['ola_set_dmx', '-u', '1', '-d', dmx_values]
    call(['ola_set_dmx', '-u', '1', '-d', dmx_values])