import jsonschema

from jsonschema import ValidationError, RefResolutionError


def validate(data, schema):
    """Validates json against a schema
    :param
        -   request:    JSON Dict to validate
        -   schema:     Schema to validate against
    :returns
        True if valid data
    """
    try:
        jsonschema.validate(data, schema)
    except (ValidationError, RefResolutionError) as jsonschema_exception:
        # TODO: Check for specific errors, like URL's that have a slash at the end, and give specific messages back
        message = f"The given data was not valid based on the given schema: {jsonschema_exception}"
        raise SchemaValidationError(message, data, schema)
    except Exception as e:
        error_message = f"Unexpected problem encountered while validating the data against the schema. Caught Exception: {e}"
        raise SchemaValidationError(error_message, data, schema)

    return True


class SchemaValidationError(Exception):
    def __init__(self, message=None, schema_data=None, schema=None, stacktrace=""):
        self.message = message
        self.data = schema_data if schema_data is not None else {}
        self.schema = schema if schema is not None else {}
        self.details = schema_data if schema_data is not None else {}

        self.code = 'SCHEMA_VALIDATION_ERROR'

    def __str__(self):
        return self.message

    def to_dict(self):
        self.details['data'] = self.data
        self.details['schema'] = self.schema
        return {
            'message': self.message,
            'code': self.code,
            'details': self.details
        }
