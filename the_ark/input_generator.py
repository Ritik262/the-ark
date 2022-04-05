from copy import deepcopy
from datetime import datetime, timedelta
from .field_handlers import DROP_DOWN_FIELD, CHECK_BOX_FIELD, RADIO_FIELD, SELECT_FIELD, BUTTON_FIELD, STRING_FIELD, \
    PHONE_FIELD, ZIP_CODE_FIELD, DATE_FIELD, INTEGER_FIELD, EMAIL_FIELD, All_FIELD_TYPES, FIELD_IDENTIFIER, PASSWORD_FIELD
import random
import string
import time
import traceback

INDEX_FIELDS = [SELECT_FIELD, DROP_DOWN_FIELD, RADIO_FIELD]
DEFAULT_STRING_MIN = 1
DEFAULT_STRING_MAX = 10
DEFAULT_INTEGER_MIN = 1
DEFAULT_INTEGER_MAX = 9
DEFAULT_INTEGER = 1
DEFAULT_INDEX_OPTIONS = 2
DEFAULT_DOMAIN = "meltmedia.com"
DEFAULT_START_DATE = str((datetime.now() - timedelta(weeks=52 * 20)).date())
DEFAULT_END_DATE = str((datetime.now() - timedelta(weeks=52 * 100)).date())
DEFAULT_DATE_FORMAT = "%m/%d/%Y"
SPECIAL_CHARACTER_LIST = ["!", "@", "#", "$", "&", "*"]


def dispatch_field(field_data, test_number=1):
    """
    Takes a 'field_data' dict object and dispatches it to the relevant input generation method based on the
    'type' key within the dict.

    :param
        - field_data:   dict - An object contain key value pairs for each of the field's parameters
        - test_number:  int - An number that specifies which submission number this generation is being used for. This
                              will help determine whether the field has been populated previously and whether to leave
                              it blank
    """
    if "type" in field_data and field_data["type"].lower() not in All_FIELD_TYPES:
        raise UnknownFieldType(field_data["type"], stacktrace=traceback.format_exc())

    try:
        required = field_data.get("required") or False
        if field_data[FIELD_IDENTIFIER].lower() == STRING_FIELD:
            return generate_string(field_data["min"], field_data["max"], test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() == INTEGER_FIELD:
            padding = field_data.get("padding") or DEFAULT_INTEGER
            return generate_integer(field_data["min"], field_data["max"], padding, test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() == EMAIL_FIELD:
            domain = field_data.get("domain") or DEFAULT_DOMAIN
            return generate_email(domain, test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() == PASSWORD_FIELD:
            return generate_password(test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() == PHONE_FIELD:
            decimal = field_data.get("decimal") or False
            parenthesis = field_data.get("parenthesis") or False
            dash = field_data.get("dash") or False
            space = field_data.get("space") or False
            return generate_phone(decimal, parenthesis, dash, space, test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() == ZIP_CODE_FIELD:
            return generate_zip_code(test_number, required)

        elif field_data[FIELD_IDENTIFIER].lower() in INDEX_FIELDS:
            always_random = field_data.get("random") or False
            return generate_index(len(field_data["enum"]), test_number, required, always_random)

        elif field_data[FIELD_IDENTIFIER].lower() == CHECK_BOX_FIELD:
            return generate_check_box(len(field_data["enum"]), test_number, required)

        else:
            # Date Field! (no elif here cause unittest coverage didn't like the branch not having an end)
            start_date = field_data.get("start_date") or DEFAULT_START_DATE
            end_date = field_data.get("end_date") or DEFAULT_END_DATE
            date_format = field_data.get("date_format") or DEFAULT_DATE_FORMAT
            return generate_date(start_date, end_date, date_format, test_number, required)

    except InputGeneratorException as ige:
        message = "Encountered an error dispatching the field"
        if "name" in field_data:
            message += f" named {field_data['name']!r}"
        ige.msg = f"{message} | {ige.msg}"
        raise ige

    except KeyError as key:
        message = f"The key {key} is missing from the field data"
        if "name" in field_data:
            message += f" for the field named {(field_data['name'])!r}"
        message += ", thus the Input Generator was unable to dispatch the field."
        raise MissingKey(message, key, stacktrace=traceback.format_exc(),
                         details={"missing_key": str(key), "field_data": field_data})

    except Exception as e_text:
        message = "An Unhandled Exception emerged while generating an input for the field"
        if "name" in field_data:
            message += f" named {field_data['name']!r}"
        message += f" | {e_text}"
        raise InputGeneratorException(message, stacktrace=traceback.format_exc())


def set_leave_blank(test_number, required):
    """Sets a generation method's values for whether to leave a field blank.
    :param
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   bool:           Whether the input for the field should be left blank
    """
    leave_blank = False

    # If the field is not required, do logic to determine whether to leave it blank upon fill
    if required is False:
        # Always fill in the field on the first test...
        if test_number != 1:
            # ... but give 25% chance to leave blank otherwise
            leave_blank = True if random.random() < .25 else False

    return leave_blank


def check_min_vs_max(min_length, max_length):
    """
    Ensures the min is not greater than the max before creating the field value within the min - max range
    :param
        -   min_length:     The low value end of the length range
        -   max_length:     The high value end of the length range
    :return:
    """
    if min_length > max_length:
        message = "The minimum cannot be greater than the maximum value"
        raise MinGreaterThanMax(message, min_length, max_length)


def generate_string(min_length=DEFAULT_STRING_MIN, max_length=DEFAULT_STRING_MAX,
                    test_number=1, required=True):
    """ Creates a str object with a length greater than min_length and less than max_length, made up of randomly
        selected upper and lowercase letters.
    :param
        -   min_length:     The minimum length, in characters, that the generated string can be. Defaults to 1
        -   max_length:     The maximum length, in characters, that the generated string can be. Defaults to 10
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   string:         The randomly generated or blank string
    """
    try:
        # Ensure the minimum and maximum values create a valid range
        check_min_vs_max(min_length, max_length)

        # Instantiate the required and leave_blank variables based on the field object and test number
        leave_blank = set_leave_blank(test_number, required)

        # Set the return to a blank string if leave_blank is true. Otherwise create a string
        if leave_blank:
            random_string = ""
        else:
            random_string = "".join(random.choice(string.ascii_letters) for num in range(random.randint(min_length,
                                                                                                        max_length)))

        return random_string

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating a String: {e_text}"
        raise InputGeneratorException(message)


def generate_integer(min_int=DEFAULT_INTEGER_MIN, max_int=DEFAULT_INTEGER_MAX,
                     padding=DEFAULT_INTEGER, test_number=1, required=True):
    """ Generates an str object with an int character that is greater that min_int and less than max_int.
    :param
        -   min_int:        The minimum value that the generated integer can be. Defaults to 1
        -   max_int:        The maximum value that the generated integer can be. Defaults to 9
        -   padding:        The number of characters the string will be. if the int created is 2 characters, but a
                            padding of 3 is given, then two leading zeroes are be added to make the int three characters
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   integer:        The randomly generated, or blank string
    """
    try:
        # Ensure the minimum and maximum values create a valid range
        check_min_vs_max(min_int, max_int)

        # Instantiate the required and leave_blank variables based on the field object and test number
        leave_blank = set_leave_blank(test_number, required)

        # Set the return to a blank string if leave_blank is true. Otherwise create an integer
        if leave_blank:
            integer = ""
        else:
            # Create the integer value between the min and max and with the padding provided
            integer = f"{random.randint(min_int, max_int):0{padding}d}"

        return integer

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating an Integer: {e_text}"
        raise InputGeneratorException(message)


def generate_email(domain=DEFAULT_DOMAIN, test_number=1, required=True):
    """ Generates a random email address in the firstname.lastname@domain format
    :param
        -   domain:         The domain address the email will be from ie. @domain. This defaults to "meltmedia.com"
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   string:         The randomly generated, or blank email string
    """
    try:
        # Instantiate variables
        leave_blank = set_leave_blank(test_number, required)
        email = ""

        # Set the return to a blank string if leave_blank is true. Otherwise create an email
        if leave_blank:
            return ""
        else:
            # - Create an email in the firstname.lastname@domain format.
            #   The first and last names are generated using the generate_string method
            first_name = generate_string(6, 10)
            last_name = generate_string(6, 10)

            if domain == DEFAULT_DOMAIN:
                email = "test+"

            email += f"{first_name}.{last_name}@{domain}"

            return email

    except Exception as e_text:
        message = "Unhandled Exception caught while generating an Email: {e_text}"
        raise InputGeneratorException(message)


def generate_password(test_number=1, required=True):
    """ Generates a random password with a capitol letter first and ends with a special character
    :param
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   string:         The randomly generated password string
    """
    try:
        first_letter = generate_string(1, 2).upper()
        number = generate_integer(1, 2)
        body = generate_string(5, 6)
        character_position = random.randint(0, len(SPECIAL_CHARACTER_LIST) - 1)
        character = SPECIAL_CHARACTER_LIST[character_position]
        password = f"{first_letter}{body}{number}{character}"

        return password

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating an Password: {e_text}"
        raise InputGeneratorException(message)


def generate_phone(decimals=False, parenthesis=False, dash=False, space=False, test_number=1, required=True):
    """ Generates a random phone number
    :param
        -   decimals:       Bool used to determine whether to put a decimals between each of the portions of the phone
                            number. When True this parameter supersedes the others as you cannot have both decimals and
                            parenthesis, or decimals and space or dash, etc.
        -   parenthesis:    Bool used to determine whether to put a parenthesis around the Area Code of the generated
                            number. The default value is False
        -   dash:           Bool used to determine whether to put a dash between the first three and last 4 digits of
                            the phone number. The default value is False
        -   space:          Bool used to determine whether to put a space between the area code and number portions
                            of the phone number. The default value is False
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   string:         The randomly generated, or blank phone number
    """
    try:
        leave_blank = set_leave_blank(test_number, required)

        # Set the return to a blank string if leave_blank is true. Otherwise create a phone number
        if leave_blank:
            phone_number = ""
        else:
            # - Generate the Area Code portion of the phone number
            # Area Code should not start with 0's or 1's
            area_code = "".join(str(random.randint(2, 9)) for x in range(0, 3))

            # - Generate the number portion of the phone number
            # The first three digits of the number should not start with 0's or 1's
            start = "".join(str(random.randint(2, 9)) for x in range(0, 3))
            finish = "".join(str(random.randint(0, 9)) for y in range(0, 4))

            # - Format the number
            # Use only the decimal formatting if the user specified they wanted decimals
            if decimals:
                phone_number = f"{area_code}.{start}.{finish}"
            else:
                # Surround the area code in parenthesis if parenthesis parameter is True
                area_code = f"({area_code})" if parenthesis else area_code

                # Format the "number" portion of the phone number
                # Dash takes precedence over space
                if dash:
                    if not space and not parenthesis:
                        number = f"-{start}-{finish}"
                    else:
                        # Add the dash between the start and finish of the number if dash parameter is True
                        number = f"{start}-{finish}"
                elif space:
                    # Add a space if space parameter is True, but dash is False
                    number = f"{start} {finish}"
                else:
                    number = f"{start}{finish}"

                # Stitch the area code and number together
                if space:
                    phone_number = f"{area_code} {number}"
                else:
                    phone_number = area_code + number

        return phone_number

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating a Phone Number: {e_text}"
        raise InputGeneratorException(message)


def generate_zip_code(test_number=1, required=True):
    """ Generates a random 5 digit string to act as a ZIP code
    :param
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether the field has been populated previously and whether to leave it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   sting:          The randomly generated, or blank ZIP Code string
    """
    try:
        leave_blank = set_leave_blank(test_number, required)

        # Set the return to a blank string if leave_blank is true. Otherwise create a zip code
        if leave_blank:
            zip_code = ""
        else:
            # - Generate the ZIP Code
            # Prevent the first number from being 0 so that it is not truncated when the output is viewed in Excel
            first = str(random.randint(1, 9))
            # The last four digits are between 0 and 9
            zip_code = first + "".join(str(random.randint(0, 9)) for z in range(0, 4))

        return zip_code

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating an Zip Code: {e_text}"
        raise InputGeneratorException(message)


def generate_index(num_of_options=DEFAULT_INDEX_OPTIONS, test_number=1, required=True, always_random=False):
    """ Calculates which option should be selected from the given field based on test number. The index is randomly
        selected after all options have been used at least once.
    :param
        -   num_of_options: The number oof options available in the list. If a field object is passed in then this
                            value is overwritten by the "enum" key for that field. Defaults to a value of 2
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether all options for the field have been used or not and whether to leave
                            it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
        -   always_random:  A bool specifying whether to always select a random index for this field. This will
                            typically be used for fields like State which have 50+ options. In these cases we want to
                            select a new item each time, but are not necessarily all options or in any particular order
    :returns
        -   integer:        The randomly generated (int), or blank index (string) to select from the field's options
    """
    try:
        leave_blank = set_leave_blank(test_number, required)

        # Set test_number to a default of 1 unless a value was passed in.
        test_number = 1 if not test_number else test_number

        random_choice = None
        all_options_used = True if test_number > num_of_options else False

        # - Always choose a random index if all options have already been sent once
        if all_options_used:
            random_choice = True

        # - Generate the input index to use when filling out this field
        if leave_blank:
            # Set the return to a blank string if leave_blank is true.
            input_index = ""
        elif random_choice or always_random:
            # Select a random index if the field is "random" or if all options have already been selected previously
            input_index = random.randint(0, num_of_options - 1)
        else:
            # Select the modulo unless the test_number and number of options is the same, then select the last index
            if test_number == num_of_options:
                input_index = num_of_options - 1
            else:
                input_index = test_number % num_of_options - 1

        return input_index

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating an input index: {e_text}"
        raise InputGeneratorException(message)


def generate_check_box(num_of_options=1, test_number=1, required=True):
    """ Calculates which check box from the list of boxes should be selected based on test number. The index is
        randomly selected after all options have been used at least once. When randomly selecting there is a chance
        that more than one of the checkboxes will be selected.
    :param
        -   num_of_options: The number oof options available in the list. If a field object is passed in then this
                            value is overwritten by the "enum" key for that field. Defaults to a value of 1
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether all options for the field have been used or not and whether to leave
                            it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   list:           A list of indexes (integers) to select from the check box list when filling out this form
    """
    try:
        leave_blank = False
        random_choice = None
        all_options_used = True if test_number > num_of_options else False

        # 25% chance of leaving the field blank if it is not required and all options have already been used
        if required is False and all_options_used:
            if random.random() < .25:
                leave_blank = True

        # Always select a random index if all options have already been used
        if all_options_used:
            random_choice = True

        input_indexes = []

        if leave_blank:
            pass
        elif random_choice and num_of_options > 1:
            # - Add at least one item to the input list
            index = random.randint(0, num_of_options - 1)
            input_indexes.append(index)

            # - 50/50 chance of adding another input index to the list
            while random.random() <= .5 and len(input_indexes) < num_of_options:
                # Cycle through indexes until finding one that is not already being used
                while index in input_indexes:
                    index = random.randint(0, num_of_options - 1)
                # Add the index to the list
                input_indexes.append(index)
        else:
            # Select the modulo unless the test_number and number of options is the same, then select the last index
            if test_number == num_of_options:
                input_indexes.append(num_of_options - 1)
            else:
                input_indexes.append(test_number % num_of_options - 1)

        return input_indexes

    except Exception as e_text:
        message = "Unhandled Exception caught while generating the Check Box input indexes: {0}".format(e_text)
        raise InputGeneratorException(message)


def generate_date(start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE, date_format=DEFAULT_DATE_FORMAT,
                  test_number=1, required=True):
    """ Generates a date in the given date format. By default this date will be -18 to -100 years ago in order to keep
        the user over the age of 18 when filling out birthdays. However these dates can be passed through if need be.
    :param
        -   start_date:     Date in "%Y-%m-%d" format or an integer specifying days. This is the default format for
                            datetime.now().date(). This date is used as the furthest back in history the generated date
                            will be. If the user sends through an integer rather than a date the integer will be used
                            to specify how many days in the past to start generating from. If the integer value is
                            negative, then the start date will be in the future. If no start date is given the date
                            100 years, or 52*100 weeks, ago will be used.
        -   end_date:       Date in "%Y-%m-%d" format or an integer specifying days. This is the default format for
                            datetime.now().date(). This date is used as the most recent day in history the generated
                            date will be. If the user sends through an integer rather than a date the integer will be
                            used to specify how many days in the past to stop generating from. If the integer value is
                            negative, then the end date will be in the future. If no end date is given an end date of
                            18 years, or 52*18 weeks, ago will be used.
        -   date_format:    The format you'd like the date to be when it is returned. This defaults to %m/%d/%Y which
                            would make a MM/DD/YYYY format. Other format examples are %y-%m-%d to get YY-MM-DD or
                            %d%m%Y to get DDMMYYYY, etc.
        -   test_number:    An int that specifies which submission number this generation is being used for. This will
                            help determine whether all options for the field have been used or not and whether to leave
                            it blank
        -   required:       A bool specifying whether the field for which input if being generated is required on the
                            form on which the input will be input
    :returns
        -   string:         A string formatted to look like a date
    """
    try:
        leave_blank = set_leave_blank(test_number, required)

        if leave_blank:
            return ""
        else:
            if isinstance(start_date, int):
                start_date = str((datetime.now() - timedelta(days=start_date)).date())
            if isinstance(end_date, int):
                end_date = str((datetime.now() - timedelta(days=end_date)).date())

            start_time = time.mktime(time.strptime(start_date, "%Y-%m-%d"))
            end_time = time.mktime(time.strptime(end_date, "%Y-%m-%d"))

            random_time = start_time + random.random() * (end_time - start_time)

            return time.strftime(date_format, time.localtime(random_time))

    except Exception as e_text:
        message = f"Unhandled Exception caught while generating a Date: {e_text}"
        raise InputGeneratorException(message)


class InputGeneratorException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(InputGeneratorException, self).__init__()

    def __str__(self):
        exception_msg = "Input Generator Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"{self.stacktrace}"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg


class MissingKey(InputGeneratorException):
    def __init__(self, message, key, stacktrace=None, details=None):
        super(MissingKey, self).__init__(msg=message, stacktrace=stacktrace, details=details)
        self.key = f"{key}"
        self.details["missing_key"] = key if details is None or "missing_key" not in details else details["missing_key"]


class MinGreaterThanMax(InputGeneratorException):
    def __init__(self, message, minimum, maximum, stacktrace=None, details=None):
        super(MinGreaterThanMax, self).__init__(msg=message, stacktrace=stacktrace, details=details)
        self.details["min"] = minimum if details is None or "min" not in details else details["min"]
        self.details["max"] = maximum if details is None or "max" not in details else details["max"]


class UnknownFieldType(InputGeneratorException):
    def __init__(self, field_type, stacktrace=None):
        message = f"""An unknown field type of {field_type!r} was passed through to the input generator dispatch method.
                  Please review the field's configuration and look for typos or field types that should
                  potentially be added."""
        super(UnknownFieldType, self).__init__(msg=message, stacktrace=stacktrace)
        self.field_type = f"{field_type}"
        self.details["unknown_field_type"] = field_type
