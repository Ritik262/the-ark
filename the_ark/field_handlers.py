from . import selenium_helpers
import traceback

FIELD_IDENTIFIER = "type"
STRING_FIELD = "string"
PHONE_FIELD = "phone"
ZIP_CODE_FIELD = "zip_code"
DATE_FIELD = "date"
INTEGER_FIELD = "integer"
EMAIL_FIELD = "email"
DROP_DOWN_FIELD = "drop_down"
CHECK_BOX_FIELD = "check_box"
RADIO_FIELD = "radio"
SELECT_FIELD = "select"
BUTTON_FIELD = "button"
PASSWORD_FIELD = "password"
TEXT_FIELD_TYPES = [STRING_FIELD, PHONE_FIELD, ZIP_CODE_FIELD, DATE_FIELD, INTEGER_FIELD, EMAIL_FIELD, PASSWORD_FIELD]
All_FIELD_TYPES = [DROP_DOWN_FIELD, CHECK_BOX_FIELD, RADIO_FIELD, SELECT_FIELD, BUTTON_FIELD] + TEXT_FIELD_TYPES


class FieldHandler:
    def __init__(self, selenium_helper):
        """
        This class contains methods which can be used to handle each field type.
        :param
            - selenium_helper:  SeleniumHelpers() - The current browser driver wrapper that is being interacted with.
        """
        self.sh = selenium_helper

    def dispatch_field(self, field):
        """
        Takes a 'field' dict object and dispatches it to the relevant handle method based on the 'type' key within the
        dict.
        Accepted types are:
        string  - Required keys: css_selector (string), input (string)
        phone   - Required keys: css_selector (string), input (string)
        date    - Required keys: css_selector (string), input (string)
        email   - Required keys: css_selector (string), input (string)
        integer - Required keys: css_selector (string), input (string)
        check_box - Required Keys: enum (list[dict]), input (list[int])
        radio   - Required Keys: enum (list[dict]), input (int)
        select  - Required Keys: css_selector (string), input (int), enum (list[string])
        drop_down - Required Keys: css_selector (string), input (int), enum (list[dict])
        button  - Required Keys: css_selector (string)

        :param
            - css_selector:    string - The element's css selector in the webpage's DOM.
            - input_text:      string - The text that is to be entered into the field.
            - confirm_css_selector:     bool - True if there is a repeated field used to confirm the entry into the
                                        first. This is typically most relevant to e-mail and password fields.
        """
        if FIELD_IDENTIFIER in field and field[FIELD_IDENTIFIER].lower() not in All_FIELD_TYPES:
            raise UnknownFieldType(field[FIELD_IDENTIFIER], stacktrace=traceback.format_exc())

        try:
            if field[FIELD_IDENTIFIER].lower() in TEXT_FIELD_TYPES:
                confirm_css_selector = field.get("confirm_css_selector") or None
                self.handle_text(field["css_selector"], field["input"], confirm_css_selector)

            if field[FIELD_IDENTIFIER].lower() == CHECK_BOX_FIELD:
                self.handle_check_box(field["enum"], field["input"])

            if field[FIELD_IDENTIFIER].lower() == RADIO_FIELD:
                self.handle_radio_button(field["enum"], field["input"])

            if field[FIELD_IDENTIFIER].lower() == SELECT_FIELD:
                # Default first_valid to False as it is the default.
                first_valid = field.get("first_valid") or False
                self.handle_select(field["css_selector"], field["input"], first_valid)

            if field[FIELD_IDENTIFIER].lower() == DROP_DOWN_FIELD:
                self.handle_drop_down(field["css_selector"], field["enum"], field["input"])

            if field[FIELD_IDENTIFIER].lower() == BUTTON_FIELD:
                self.handle_button(field["css_selector"])

        except FieldHandlerException as fhe:
            message = "Encountered an error dispatching the field"
            if "name" in field:
                message += f" named {field['name']!r}"
            fhe.msg = f"{message} | {fhe.msg}"
            raise fhe

        except KeyError as key:
            message = f"The key {key} is missing from the field data"
            if "name" in field:
                message += f" for the field named {field['name']!r}"
            message += " and so the Field Handler was unable to dispatch the field."
            raise MissingKey(message, key, stacktrace=traceback.format_exc(),
                             details={"missing_key": str(key), "field_data": field})

        except Exception as e_text:
            message = "An Unhandled Exception emerged while handling the field"
            if "name" in field:
                message += f" named {field['name']!r}"
            message += f" | {e_text}"
            raise FieldHandlerException(message, stacktrace=traceback.format_exc())

    def handle_text(self, css_selector="", input_text="", confirm_css_selector=None):
        """
        Logic used to fill in a text field. This method uses the selenium helpers class to interact with the field.

        :param
            - css_selector:    string - The element's css selector in the webpage's DOM.
            - input_text:      string - The text that is to be entered into the field.
            - confirm_css_selector:     bool - True if there is a repeated field used to confirm the entry into the
                                             first. This is typically most relevant to e-mail and password fields.
        """
        try:
            # - Handle the field
            self.sh.fill_an_element(css_selector=css_selector, fill_text=input_text)
            # Fill in the confirm field as well, if provided
            if confirm_css_selector:
                self.sh.fill_an_element(css_selector=confirm_css_selector, fill_text=input_text)

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while handling the text field."
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while filling a Text field: {e_text}"
            raise FieldHandlerException(message)

    def handle_check_box(self, enums, input_indexes):
        """
        Logic used to fill in a check box button field. This method uses the selenium helpers class to interact with
        the field.

        :param
            - enum:          list[dict] - A list of dictionary objects. Each dictionary should contain a 'css_selector'
                                        for the element and a 'value' key representing the text that corresponds with
                                        that check box option on the form.
            - input_indexes: list[int] - A list of integers. Each integer corresponds with an index in the enum list.
                                       The dict at this index is then used to determine which css_selector is clicked.
                                       Because you can select multiple check boxes in a field you can have multiple
                                       input indexes in the list.
        """
        current_test_index = "N/A"
        try:
            # - Handle the field
            for index in input_indexes:
                current_test_index = index
                self.sh.click_an_element(css_selector=enums[index]["css_selector"])

        except KeyError as key:
            message = f"Key {key} is missing from the dictionary at index {current_test_index} in the enum list: {enums[current_test_index]}"
            raise MissingKey(message, key, stacktrace=traceback.format_exc())

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while attempting to click the check box at the given enum's index."
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while filling a Check Box field: {e_text}"
            raise FieldHandlerException(message)

    def handle_radio_button(self, enums, input_index):
        """
        Logic used to fill in a radio button field. This method uses the selenium helpers class to interact with the
        field.

        :param
            - enum:         list[dict] - A list of dictionary objects. Each dictionary should contain a 'css_selector'
                                        for the element and a 'value' key representing the text that corresponds with
                                        that check box option on the form.
            - input_text:   int - This integer corresponds with an index in the enum list. The dict at this index is
                                then used to determine which css_selector is clicked.
        """
        try:
            # - Handle the field
            self.sh.click_an_element(css_selector=enums[input_index]["css_selector"])

        except KeyError as key:
            message = f"Key {key} is missing from the dictionary at index {input_index} in the enum list: {enums[input_index]}"
            raise MissingKey(message, key, stacktrace=traceback.format_exc())

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while attempting to click the radio button at the given enum's index."
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while filling a Radio Button field: {e_text}"
            raise FieldHandlerException(message)

    def handle_select(self, css_selector, input_index, first_valid=False):
        """
        Logic used to fill in a select field. This method will find the select tag of the field via the css_selector
        and then choose the option that corresponds with the given index value. This method uses the selenium helpers
        class to interact with the field.

        :param
            - css_selector:     string - The <select> tag element's css selector in the webpage's DOM.
            - input_text:       int - This integer corresponds with the index of the option that will be selected from
                                    the drop down
            - first_valid       bool - True if the first option under the select tag is a valid selection.
        """
        try:
            # Create an index offset to manage the difference in Zero Base numbering between lists and :nth-child()
            index_offset = 2
            if first_valid:
                index_offset = 1

            self.sh.click_an_element(css_selector=f"{css_selector} option:nth-child({(input_index + index_offset)})")

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while attempting to select the given select option element."
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while filling a Select field: {e_text}"
            raise FieldHandlerException(message)

    def handle_drop_down(self, css_selector, enums, input_index):
        """
        Logic used to fill in a drop down field. This method is used when the 'parent' element of drop down is
        separated from the options list element. The parent is clicked in order to make the option list elements
        visible. The css selector for the input element is then clicked.

        :param
            - css_selector:     string - The 'parent' element's css selector in the webpage's DOM.
            - enum:             list[dict] - A list of dictionary objects. Each dictionary should contain a
                                           'css_selector' for the element and a 'value' key representing the text that
                                           corresponds with that check box option on the form.
            - input_text:       int - This integer corresponds with the index of the option, in the enum list, that
                                    will be selected from the drop down
        """
        try:
            # - Handle the field
            # Click the parent element to reveal the options
            self.sh.click_an_element(css_selector=css_selector)
            # Click the option that corresponds with the css_selector in the given index of the enum
            self.sh.click_an_element(css_selector=enums[input_index]["css_selector"])

        except KeyError as key:
            message = f"Key {key} is missing from the dictionary at " \
                      f"index {input_index} in the enum list: {(enums[input_index])}"
            raise MissingKey(message, key)

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while attempting to select the given select option element."
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while filling a Drop Down field: {e_text}"
            raise FieldHandlerException(message)

    def handle_button(self, css_selector):
        """
        Logic used to click a button field element. This can be used to navigate between form pages that have a 'Next'
        button. Or to submit the form by clicking the submit button.

        :param
            - css_selector:     string - The element's css selector in the webpage's DOM.
        """
        try:
            self.sh.click_an_element(css_selector=css_selector)

        except selenium_helpers.SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while attempting to select click the button"
            error = SeleniumError(message, selenium_error)
            raise error

        except Exception as e_text:
            message = f"An Unhandled Exception emerged while attempting to click the button: {e_text}"
            raise FieldHandlerException(message)


class FieldHandlerException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(FieldHandlerException, self).__init__()

    def __str__(self):
        exception_msg = "Field Handler Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"{self.stacktrace}"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg


class MissingKey(FieldHandlerException):
    def __init__(self, message, key, stacktrace=None, details=None):
        super(MissingKey, self).__init__(msg=message, stacktrace=stacktrace, details=details)
        self.key = f"{key}"
        if details:
            self.details["missing_key"] = details.get("missing_key") or key


class SeleniumError(FieldHandlerException):
    def __init__(self, message, selenium_helper_exception):
        new_message = f"{message} | {selenium_helper_exception.msg}"
        super(SeleniumError, self).__init__(msg=new_message,
                                            stacktrace=selenium_helper_exception.stacktrace,
                                            details=selenium_helper_exception.details)


class UnknownFieldType(FieldHandlerException):
    def __init__(self, field_type, stacktrace=None):
        message = f"""An unknown field type of {field_type!r} was passed through to the field handler dispatch method.
                  Please review the field's configuration and look for typos or field types that should
                  potentially be added."""
        super(UnknownFieldType, self).__init__(msg=message, stacktrace=stacktrace)
        self.field_type = f"{field_type}"
        self.details["unknown_field_type"] = field_type