from django.conf.urls import url
from alfred.graphql import Schema
from graphene_django.views import GraphQLView

urlpatterns = [
    url(r'^$', GraphQLView.as_view(schema=Schema())),
]
