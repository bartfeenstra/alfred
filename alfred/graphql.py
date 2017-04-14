import graphene
from alfred.lights import dmx_set_values, dmx_get_values


class SetLightsType(graphene.InputObjectType):
    red = graphene.NonNull(graphene.Int)
    blue = graphene.NonNull(graphene.Int)
    green = graphene.NonNull(graphene.Int)
    luminosity = graphene.NonNull(graphene.Int)


class LightsType(graphene.ObjectType):
    red = graphene.NonNull(graphene.Int)
    blue = graphene.NonNull(graphene.Int)
    green = graphene.NonNull(graphene.Int)
    luminosity = graphene.NonNull(graphene.Int)


class SetLights(graphene.Mutation):
    class Input:
        lights = graphene.Argument(SetLightsType)

    lights = graphene.Field(lambda: LightsType)

    @staticmethod
    def mutate(root, args, context, info):
        dmx_values = args.get('lights')
        dmx_values = dmx_set_values(dmx_values['red'], dmx_values['green'], dmx_values['blue'], dmx_values['luminosity'])
        lights_output = LightsType()
        lights_output.red = dmx_values['red']
        lights_output.green = dmx_values['green']
        lights_output.blue = dmx_values['blue']
        lights_output.luminosity = dmx_values['luminosity']
        return SetLights(lights=lights_output)


class Query(graphene.ObjectType):
    lights = graphene.Field(LightsType)

    def resolve_lights(self, args, context, info):
        return dmx_get_values()


class Mutation(graphene.ObjectType):
    set_lights = SetLights.Field()


class Schema(graphene.Schema):
    def __init__(self):
        graphene.Schema.__init__(self, query=Query, mutation=Mutation)
