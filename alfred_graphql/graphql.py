import graphene
from alfred.lights import dmx_set_values, dmx_get_values


class SetLightsType(graphene.InputObjectType):
    color = graphene.NonNull(graphene.String)
    luminosity = graphene.NonNull(graphene.Int)


class LightsType(graphene.ObjectType):
    color = graphene.NonNull(graphene.String)
    luminosity = graphene.NonNull(graphene.Int)


class SetLights(graphene.Mutation):
    class Input:
        lights = graphene.Argument(SetLightsType)

    lights = graphene.Field(lambda: LightsType)

    @staticmethod
    def mutate(root, args, context, info):
        lights_input = args.get('lights')
        dmx_values = dmx_set_values(lights_input['color'],
                                    lights_input['luminosity'])
        lights_output = LightsType()
        lights_output.color = dmx_values['color']
        lights_output.luminosity = dmx_values['luminosity']
        return SetLights(lights=lights_output)


class Query(graphene.ObjectType):
    lights = graphene.Field(LightsType)

    def resolve_lights(self, args, context, info):
        dmx_values = dmx_get_values()
        lights_output = LightsType()
        lights_output.color = dmx_values['color']
        lights_output.luminosity = dmx_values['luminosity']
        return lights_output


class Mutation(graphene.ObjectType):
    set_lights = SetLights.Field()


class Schema(graphene.Schema):
    def __init__(self):
        graphene.Schema.__init__(self, query=Query, mutation=Mutation)
