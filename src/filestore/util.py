from typing import Any

from pydantic.json_schema import GenerateJsonSchema, JsonSchemaWarningKind, DEFAULT_REF_TEMPLATE, JsonSchemaMode
from pydantic import BaseModel, ConfigDict


class NoDefaultSchema(GenerateJsonSchema):
    ignored_warning_kinds: set[JsonSchemaWarningKind] = {'skipped-choice', 'non-serializable-default'}


class FormModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = NoDefaultSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        return super().model_json_schema(by_alias=by_alias, ref_template=ref_template,
                                         schema_generator=schema_generator, mode=mode)
