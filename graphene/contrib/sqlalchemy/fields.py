from graphene import relay
from graphene.contrib.sqlalchemy.utils import get_type_for_model, lazy_map
from graphene.core.fields import Field, LazyField, ListField
from graphene.relay.utils import is_node


class SQLAlchemyConnectionField(relay.ConnectionField):

    def wrap_resolved(self, value, instance, args, info):
        schema = info.schema.graphene_schema
        return lazy_map(value, self.get_object_type(schema))


class LazyListField(ListField):

    def resolve(self, instance, args, info):
        schema = info.schema.graphene_schema
        resolved = super(LazyListField, self).resolve(instance, args, info)
        return lazy_map(resolved, self.get_object_type(schema))


class ConnectionOrListField(LazyField):

    def get_field(self, schema):
        model_field = self.field_type
        field_object_type = model_field.get_object_type(schema)
        if is_node(field_object_type):
            field = SQLAlchemyConnectionField(model_field)
        else:
            field = LazyListField(model_field)
        field.contribute_to_class(self.object_type, self.name)
        return field


class SQLAlchemyModelField(Field):

    def __init__(self, model, *args, **kwargs):
        super(SQLAlchemyModelField, self).__init__(None, *args, **kwargs)
        self.model = model

    def resolve(self, instance, args, info):
        resolved = super(SQLAlchemyModelField, self).resolve(instance, args, info)
        schema = info.schema.graphene_schema
        _type = self.get_object_type(schema)
        assert _type, ("Field %s cannot be retrieved as the "
                       "ObjectType is not registered by the schema" % (
                           self.attname
                       ))
        return _type(resolved)

    def internal_type(self, schema):
        _type = self.get_object_type(schema)
        if not _type and self.object_type._meta.only_fields:
            raise Exception(
                "Model %r is not accessible by the schema. "
                "You can either register the type manually "
                "using @schema.register. "
                "Or disable the field %s in %s" % (
                    self.model,
                    self.attname,
                    self.object_type
                )
            )
        return schema.T(_type) or Field.SKIP

    def get_object_type(self, schema):
        return get_type_for_model(schema, self.model)