import time
from urllib.parse import urlparse, urljoin

from the_ark import input_generator
from the_ark.field_handlers import STRING_FIELD, EMAIL_FIELD, PHONE_FIELD, ZIP_CODE_FIELD, DATE_FIELD
from the_ark.resources.action_constants import *
from the_ark.selenium_helpers import SeleniumHelperExceptions


class Actions:
    def __init__(self, selenium_helper):
        self.sh = selenium_helper
        self.iteration = 0

    def dispatch_list_of_actions(self, action_list, element=None):
        """
        Dispatch a list of actions into their proper methods. The "action" key in the action object needs to match the
        name of the action method you plan to call. This should be verified before sending in here by validating the
        list against the JSON schema in action_schema.py

        :param action_list: A list of action objects that passed a schema check against the action_schema
        :param element: A webdriver element that is used when performing for_each actions
        """
        try:
            for action in action_list:
                self.dispatch_action(action, element)
        except TypeError as e:
            raise ActionException(f"Please ensure you pass through a list type in the action_list paramater | {e}")

    def dispatch_action(self, action, element=None):
        """
        Dispatch a single action object
        """
        action_type = "Not-Instantiated"
        try:
            action_type = action[ACTION_KEY]
            getattr(self, action_type)(action, element)

        except SeleniumHelperExceptions as selenium_error:
            message = f"A Selenium error was caught while performing a {action_type!r} action. {selenium_error}"
            raise ActionException(message)

        except KeyError as key_error:
            message = f"A KeyError Exception for the key named {key_error} was raised while performing a {action_type!r} action! " \
                      "Check the spelling of the key and/or update the configuration schema" \
                      "to include a check for the proper key's existence"
            raise ActionException(message)

        except AttributeError as attr_error:
            message = f"An AttributeError Exception was raised while performing a {action_type!r} action! Check the spelling " \
                      "of the action and/or update the configuration schema to include a check " \
                      f"for the proper naming of this action. Error: {attr_error}"
            raise ActionException(message)

        except Exception as actions_error:
            raise ActionException(f"An error occurred while performing a {action_type!r} "
                                  f"action on {(self.sh.get_current_url or 'No-URL')} | {actions_error}")

    def load_url(self, action, element=None):
        """
        Load a new url.
        If only a "path" is given then that path will be added to the current domain.
        If only a "url" is given it will load directly to that url
        If both a "url" and a "path" are given then the path will be added to the end of that url and attempted to load
        """
        path = action.get(PATH_KEY)
        url = action.get(URL_KEY)

        if url and path:
            url += path

        if path and not url:
            url_parse = urlparse(self.sh.get_current_url())
            base = f"{url_parse.scheme}://{url_parse.netloc}"
            url = urljoin(base, path)

        self.sh.load_url(url, action.get(BYPASS_404_KEY))

    def click(self, action, element=None):
        """
        Click an element.
        If an element is given then that element will be clicked
        If no element is given then the "css_selector" value in the action object will be used to find an element.
        """
        if element and action.get(ELEMENT_KEY):
            self.sh.click_an_element(web_element=element)
        else:
            self.sh.click_an_element(action[CSS_SELECTOR_KEY])

    def hover(self, action, element=None):
        """
        Hover the mouse over an element.
        If an element is given then that element will be hovered
        If no element is given then the "css_selector" value in the action object will be used to find an element.
        """
        if element and action.get(ELEMENT_KEY):
            self.sh.hover_on_element(web_element=element)
        else:
            self.sh.hover_on_element(action[CSS_SELECTOR_KEY])

    def enter_text(self, action, element=None):
        """
        Enter text into an input field.
        If an "input_type" is given, the input_generator will generate an input of that type and fill the field.
        Otherwise the action object's "input" value will be entered.

        If an element is given then that element will be filled
        If no element is given then the "css_selector" value in the action object will be used to find an element.
        """
        if action.get(INPUT_TYPE_KEY):
            input_type = action.get(INPUT_TYPE_KEY)
            if input_type == STRING_FIELD:
                text = input_generator.generate_string()
            elif input_type == EMAIL_FIELD:
                text = input_generator.generate_email()
            elif input_type == ZIP_CODE_FIELD:
                text = input_generator.generate_zip_code()
            elif input_type == PHONE_FIELD:
                text = input_generator.generate_phone()
            elif input_type == DATE_FIELD:
                text = input_generator.generate_date()
            else:
                raise ActionException(f"The given input type of {input_type!r} is not a known type and we could not generate text for this action")
        else:
            text = action[INPUT_KEY]

        if element and action.get(ELEMENT_KEY):
            self.sh.fill_an_element(text, web_element=element)
        else:
            self.sh.fill_an_element(text, action[CSS_SELECTOR_KEY])

    def scroll_window_to_position(self, action, element=None):
        """
        Scrolls the window to a specific scroll position. This position is absolute and not relative to the current
        scroll position of the browser window.
        You can scroll up/down or sideways. As well as directly to the top or bottom of the page.
        """
        self.sh.scroll_window_to_position(action.get(Y_POSITION_KEY, 0),
                                          action.get(X_POSITION_KEY, 0),
                                          action.get(POSITION_TOP_KEY, 0),
                                          action.get(POSITION_BOTTOM_KEY, 0))

    def scroll_window_to_element(self, action, element=None):
        """
        Scrolls the window to a specific element on the page.
        You can specify whether you'd like the element to appear at the top, middle, or bottom of the screen after the
        scroll has taken place
        """
        if element and action.get(ELEMENT_KEY):
            self.sh.scroll_to_element(web_element=element,
                                      position_bottom=action.get(POSITION_BOTTOM_KEY),
                                      position_middle=action.get(POSITION_MIDDLE_KEY))
        else:
            self.sh.scroll_to_element(action[CSS_SELECTOR_KEY],
                                      position_bottom=action.get(POSITION_BOTTOM_KEY),
                                      position_middle=action.get(POSITION_MIDDLE_KEY))

    def scroll_an_element(self, action, element=None):
        y_pos = action.get(Y_POSITION_KEY)
        x_pos = action.get(X_POSITION_KEY)
        padding = action.get(SCROLL_PADDING_KEY)
        top = action.get(POSITION_TOP_KEY)
        bottom = action.get(POSITION_BOTTOM_KEY)

        if element and action.get(ELEMENT_KEY):
            self.sh.scroll_an_element(web_element=element, y_position=y_pos, x_position=x_pos,
                                      scroll_padding=padding, scroll_top=top, scroll_bottom=bottom)
        else:
            self.sh.scroll_an_element(css_selector=action[CSS_SELECTOR_KEY], y_position=y_pos,
                                      x_position=x_pos, scroll_padding=padding, scroll_top=top,
                                      scroll_bottom=bottom)

    def refresh(self, action, element=None):
        self.sh.refresh_driver()

    def sleep(self, action, element=None):
        time.sleep(action[DURATION_KEY])

    def wait_for_element(self, action, element=None):
        self.sh.wait_for_element(action[CSS_SELECTOR_KEY], action.get(DURATION_KEY, 15))

    def send_special_key(self, action, element=None):
        self.sh.send_special_key(action[SPECIAL_KEY_KEY])

    def show_element(self, action, element=None):
        if element and action.get(ELEMENT_KEY):
            self.sh.show_element(web_element=element)
        else:
            self.sh.show_element(action[CSS_SELECTOR_KEY])

    def hide_element(self, action, element=None):
        if element and action.get(ELEMENT_KEY):
            self.sh.hide_element(web_element=element)
        else:
            self.sh.hide_element(action[CSS_SELECTOR_KEY])

    def execute_script(self, action, element=None):
        if element and action.get(ELEMENT_KEY):
            self.sh.execute_script(action[SCRIPT_KEY], element)
        else:
            self.sh.execute_script(action[SCRIPT_KEY])

    def switch_window_handle(self, action, element=None):
        index = action.get(INDEX_KEY)
        if index is not None:
            handles = self.sh.get_window_handles()
            self.sh.switch_window_handle(handles[index])
        else:
            self.sh.switch_window_handle()

    def close_window(self, action, element=None):
        self.sh.close_window()

    def for_each(self, action, element=None):
        elements = []

        # Stop the action if there are no elements that match the given css selector for the action.
        if not self.sh.element_exists(action[CSS_SELECTOR_KEY]):
            # Get pissed if the allow_empty key is True or not given
            if not action.get(ALLOW_EMPTY_KEY):
                message = f"There were no elements found using the css selector {action[CSS_SELECTOR_KEY]!r}. Exiting the for_each action and " \
                          "continuing with the remaining actions on this page"
                raise ActionException(message)
        else:
            elements = self.sh.get_list_of_elements(action[CSS_SELECTOR_KEY])

        for element in elements:
            if not action.get(DO_NOT_INCREMENT_KEY):
                self.iteration += 1
            self.dispatch_list_of_actions(action[ACTION_LIST_KEY], element=element)

        if not action.get(CHILD_KEY):
            self.iteration = 0


class ActionException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(ActionException, self).__init__()

    def __str__(self):
        exception_msg = "Action Class Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"{self.stacktrace}"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg
