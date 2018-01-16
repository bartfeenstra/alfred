import abc
from copy import copy
from typing import Dict, List, Tuple

from contracts import contract, ContractsMeta, with_metaclass

from alfred_json.type import IdentifiableDataType, DataType


class Rewriter(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    @contract
    def rewrite(self, schema: Dict) -> Dict:
        pass


class IdentifiableDataTypeAggregator(Rewriter):
    """
    Rewrites a JSON Schema's IdentifiableDataTypes.
    """

    @contract
    def _rewrite_data_type(self, data_type: DataType,
                           definitions: Dict) -> Tuple:
        """
        Rewrites an IdentifiableDataType.
        """
        if isinstance(data_type, IdentifiableDataType):
            definitions.setdefault(data_type.group_name, {})
            if data_type.name not in definitions[data_type.group_name]:
                # Set a placeholder definition to avoid infinite loops.
                definitions[data_type.group_name][data_type.name] = {}
                # Rewrite the type itself, because it may contain further
                # types.
                schema, definitions = self._rewrite(data_type.get_json_schema(), definitions)
                definitions[data_type.group_name][data_type.name] = schema
            return {
                       '$ref': '#/definitions/%s/%s' % (data_type.group_name,
                                                        data_type.name),
                   }, definitions
        else:
            # Rewrite the type itself, because it may contain further
            # types.
            return self._rewrite(data_type.get_json_schema(), definitions)

    def rewrite(self, schema):
        schema, definitions = self._rewrite(schema, {})
        for data_type, data_definitions in definitions.items():
            for data_name, data_definition in data_definitions.items():
                # There is no reason we should omit empty definitions,
                #  except that existing code does not always expect them.
                schema.setdefault('definitions', {})
                schema['definitions'].setdefault(data_type, {})
                schema['definitions'][data_type][data_name] = data_definition

        return schema

    @contract
    def _rewrite(self, data, definitions: Dict) -> Tuple:
        data = copy(data)
        definitions = copy(definitions)
        # @todo
        # @todo Rewrite non-identifiable type as well, just don't aggregate them.
        # @todo
        # @todo
        if isinstance(data, DataType):
            return self._rewrite_data_type(data, definitions)
        if isinstance(data, List):
            for index, item in enumerate(data):
                data[index], definitions = self._rewrite(item, definitions)
            return data, definitions
        elif isinstance(data, Dict):
            for key, item in data.items():
                data[key], definitions = self._rewrite(item, definitions)
            return data, definitions
        return data, definitions


class NestedRewriter(Rewriter):
    def __init__(self):
        super().__init__()
        self._rewriters = []

    @contract
    def add_rewriter(self, rewriter: Rewriter):
        self._rewriters.append(rewriter)

    def rewrite(self, schema):
        for rewriter in self._rewriters:
            schema = rewriter.rewrite(schema)
        return schema
