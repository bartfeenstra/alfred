import graphene
from alfred.lights import dmx_set_values


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
        lights = args.get('lights')
        dmx_set_values(lights['red'], lights['green'], lights['blue'], lights['luminosity'])


class Query(graphene.ObjectType):
    lights = graphene.Field(LightsType)

    def resolve_lights(self, args, context, info):
        return {
            "red": 0,
            "green": 0,
            "blue": 0,
            "luminosity": 0,
        }


class Mutation(graphene.ObjectType):
    set_lights = SetLights.Field()


class Schema(graphene.Schema):
    def __init__(self):
        graphene.Schema.__init__(self, query=Query, mutation=Mutation)
