import logging
import requests
import traceback
from urllib.parse import urlparse

from selenium import common
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as expected_condition
from selenium.webdriver.support.ui import WebDriverWait


class SeleniumHelpers:
    def __init__(self):
        """
        Methods to do various and repeatable selenium tasks.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.desired_capabilities = {}

    def create_driver(self, **desired_capabilities):
        """
        Creating a driver with the desired settings.
        :param
            -   desired_capabilities:   dictionary - Settings used to set up the desired browser.
        """
        try:
            if desired_capabilities.get("username") and desired_capabilities.get("access_key"):
                sauce_url = f"http://{(desired_capabilities['username'])}:{(desired_capabilities['access_key'])}@ondemand.saucelabs.com:80/wd/hub"
                self.driver = webdriver.Remote(desired_capabilities=desired_capabilities, command_executor=sauce_url)
            elif desired_capabilities.get("mobile"):
                self.driver = webdriver.Remote(desired_capabilities=desired_capabilities)
            elif desired_capabilities.get("browserName").lower() == "chrome":
                executable = desired_capabilities.get("webdriver", "chromedriver")
                options = webdriver.ChromeOptions()

                # Set the location of the Chrome binary you'd like to run.
                if desired_capabilities.get("binary"):
                    options.binary_location = desired_capabilities.get("binary")

                # Configure browser options for headless use if specified
                if desired_capabilities.get("headless"):
                    options.add_argument("headless")
                    options.add_argument("disable-gpu")

                # Update the scale factor (default is 2 in Chrome). Affects the resolution of screenshots, etc.
                if desired_capabilities.get("scale_factor"):
                    options.add_argument(f"force-device-scale-factor={(desired_capabilities['scale_factor'])}")

                self.driver = webdriver.Chrome(desired_capabilities=desired_capabilities,
                                               executable_path=executable,
                                               chrome_options=options)
            elif desired_capabilities.get("browserName").lower() == "firefox":
                binary = FirefoxBinary(desired_capabilities["binary"]) if "binary" in desired_capabilities else None
                executable = desired_capabilities.get("webdriver", "geckodriver")
                options = webdriver.FirefoxOptions()
                profile = webdriver.FirefoxProfile()

                # Configure browser options for headless use if specified
                if desired_capabilities.get("headless"):
                    # Format scale factor into a string to match the firefox Spec
                    scale_factor = f"{(desired_capabilities.get('scale_factor', 1))}.0"
                    profile.set_preference("layout.css.devPixelsPerPx", scale_factor)
                    options.add_argument("--headless")

                self.driver = webdriver.Firefox(firefox_binary=binary,
                                                executable_path=executable,
                                                firefox_profile=profile, firefox_options=options)
            elif desired_capabilities.get("browserName").lower() == "phantomjs":
                binary_path = desired_capabilities.get("binary", "phantomjs")
                self.driver = webdriver.PhantomJS(binary_path)
            elif desired_capabilities.get("browserName").lower() == "safari":
                self.driver = webdriver.Safari()
            else:
                message = f"No driver has been created. Pass through the needed desired capabilities in order to create a driver. | Desired Capabilities: {desired_capabilities}"
                raise DriverAttributeError(msg=message)

            # Set the desired_capabilities variable on the class if the browser creation was successful
            self.desired_capabilities = desired_capabilities

            return self.driver
        except Exception as driver_creation_error:
            message = f"There was an issue creating a driver with the specified desired capabilities: {desired_capabilities}\n{driver_creation_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def resize_browser(self, width=None, height=None):
        """
        This will resize the browser with the given width and/or height.
        :param
            -   width:  integer - The number the width of the browser will be re-sized to.
            -   height: integer - The number the height of the browser will be re-sized to.
        """
        try:
            if not width and not height:
                pass
            elif width and height:
                self.driver.set_window_size(width, height)
            elif width:
                self.driver.set_window_size(width, self.driver.get_window_size()["height"])
            else:
                self.driver.set_window_size(self.driver.get_window_size()["width"], height)
        except Exception as resize_error:
            message = f"Unable to resize the browser with the given width ({width}) and/or height ({height}) value(s)\n{resize_error}"
            raise DriverSizeError(msg=message, stacktrace=traceback.format_exc(), width=width, height=height)

    def get_window_size(self, get_only_width=False, get_only_height=False):
        """
        This will return the width and/or height of the full window. These numbers will include the address bar,
        favorites bar, etc.
        :param
            -   get_only_width: boolean - Whether or not to just return the width of the window.
            -   get_only_height:    boolean - Whether or not to just return the height of the window.
        :return
            -   window_width: integer - The number the width of the window is at.
            -   window_height:    integer - The number the height of the window is at.
        """
        try:
            window_size = self.driver.get_window_size()
            if get_only_width and not get_only_height:
                window_width = window_size["width"]
                return window_width
            elif get_only_height and not get_only_width:
                window_height = window_size["height"]
                return window_height
            else:
                return window_size["width"], window_size["height"]
        except Exception as get_window_size_error:
            message = f"Unable to get the width and/or the height of the window.\n {get_window_size_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def get_content_height(self, css_selector="html"):
        """
        This will return the content height of a website based on an element height. The element is defaulted to 'html'
        but a custom CSS Selector can be passed in if 'html' does not get the full height of the content.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
        :return
            - integer - The height of the content area based on the css_selector used.
        """
        try:
            return int(round(self.get_element_size(css_selector)))
        except Exception as script_error:
            message = "Unable to get the height of the page content.\n{script_error}"
            raise DriverURLError(msg=message, stacktrace=traceback.format_exc())

    def load_url(self, url, bypass_status_code_check=False):
        """
        This will check to see if the status code of the URL is not 4XX or 5XX and navigate to the URL. If the
        bypass_status_code_check is set to True it will just navigate to the given URL.
        :param
            -   url:    string - A valid URL (e.g. "http://www.duckduckgo.com")
            -   bypass_status_code_check:   boolean - Navigate to the given URL without checking the status code or not.
        """
        try:
            if bypass_status_code_check:
                self.driver.get(url)
            else:
                url_request = requests.get(url)
                if url_request.status_code == requests.codes.ok:
                    self.driver.get(url)
                else:
                    message = f"The URL: {url} has the status code of: {url_request.status_code}. You may bypass the status code check if you need to navigate to this URL."
                    raise DriverURLError(msg=message, desired_url=url)
        except Exception as get_url_error:
            message = f"Unable to navigate to the desired URL: {url}\n{get_url_error}"
            raise DriverURLError(msg=message, stacktrace=traceback.format_exc(), desired_url=url)

    def get_current_url(self):
        """
        This will get and return the URL the driver is currently on.
        :return
            -   current_url:  string - The current URL the driver is on.
        """
        try:
            current_url = self.driver.current_url
            return current_url
        except Exception as get_current_url_error:
            message = f"Unable to get the URL the driver is currently on.\n{get_current_url_error}"
            raise DriverURLError(msg=message, stacktrace=traceback.format_exc())

    def refresh_driver(self):
        """
        This will refresh the page the driver is currently on.
        """
        try:
            self.driver.refresh()
        except Exception as refresh_driver_error:
            message = f"Unable to refresh the driver.\n{refresh_driver_error}"
            raise DriverURLError(msg=message, stacktrace=traceback.format_exc())

    def get_viewport_size(self, get_only_width=False, get_only_height=False):
        """
        This will get the width and/or height of the viewport. The reason for not using driver.get_window_size here
        instead is because it's not just getting the height of the viewport but the whole window (address bar,
        favorites bar, etc.). In order to be accurate this uses the execute_script method with scripts to get the
        clientWidth and/or clientHeight.
        :param
            -   get_only_width: boolean - Whether or not to just return the width of the viewport.
            -   get_only_height:    boolean - Whether or not to just return the height of the viewport.
        :return
            -   viewport_width: integer - The number the width of the viewport is at.
            -   viewport_height:    integer - The number the height of the viewport is at.
        """
        try:
            viewport_width = self.execute_script("return document.documentElement.clientWidth;")
            viewport_height = self.execute_script("return document.documentElement.clientHeight;")
            if get_only_width and not get_only_height:
                logging.info(f"Viewport width {viewport_width}")
                return viewport_width
            elif get_only_height and not get_only_width:
                logging.info(f"Viewport height {viewport_height}")
                return viewport_height
            else:
                logging.info(f"Viewport size {viewport_width} {viewport_height}")
                return viewport_width, viewport_height
        except Exception as get_viewport_size_error:
            message = f"Unable to get the width and/or the height of the viewport.\n{get_viewport_size_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def get_window_handles(self, get_current=None):
        """
        This will get and return a list of windows or tabs currently open.
        :return
            -   current_handle:  unicode - The current window handle of the driver.
            -   window_handles:    list - A list of the current windows or tabs open in the driver.
        """
        try:
            if get_current:
                current_handle = self.driver.current_window_handle
                return current_handle
            else:
                window_handles = self.driver.window_handles
                return window_handles
        except Exception as get_handle_error:
            message = f"Unable to get window handle(s).\n{get_handle_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def switch_window_handle(self, specific_handle=None):
        """
        This will either switch to a specified window handle or the latest window handle.
        :param
            -   specific_handle:    unicode - The specific window handle to switch to in the driver.
        """
        try:
            if specific_handle:
                self.driver.switch_to.window(specific_handle)
            else:
                window_handles = self.get_window_handles()
                self.driver.switch_to.window(window_handles[-1])
        except Exception as window_handle_error:
            message = f"Unable to switch window handles.\n{window_handle_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def get_screenshot_base64(self):
        """
        Get image data as base64 of the current page.
        :return
            -   base64_image:  base64 - Image data of the current page.
        """
        try:
            base64_image = self.driver.get_screenshot_as_base64()
            return base64_image
        except Exception as base64_error:
            message = f"Unable to get screenshot as base64. The browser might have been closed.\n{base64_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())




    def save_screenshot_as_file(self, file_path, file_name):
        """
        Capture a screenshot of the current page. The file path and file name are both required. The file_name needs to
        include the file extension.
        :param
            -   file_path:  string - The path the image will be saved to.
            -   file_name:  string = The name that the image will be saved with, including the extension.
        """
        try:
            self.driver.get_screenshot_as_file(file_path + file_name)
        except TypeError as screenshot_error:
            message = f"Unable to save screenshot {file_name!r} to {file_path!r} on: {self.driver.current_url}\n{screenshot_error}"
            raise ScreenshotError(msg=message, stacktrace=traceback.format_exc(), current_url=self.driver.current_url,
                                  file_name=file_name, file_path=file_path)
        except Exception as unexpected_error:
            message = f"Unable to save screenshot {file_name!r} to {file_path}. The browser might have been closed.\n{unexpected_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def close_window(self):
        """
        This will close the active window of the driver.
        """
        try:
            self.driver.close()
        except Exception as close_error:
            message = f"Unable to close the current window. Is it possible you already closed the window?\n{close_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def quit_driver(self):
        """
        This will quit the driver.
        """
        try:
            self.driver.quit()
        except Exception as quit_error:
            message = f"Unable to quit the driver. Is it possible you already quit the driver?\n{quit_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def element_exists(self, css_selector):
        """
        This will ensure that an element exists on the page under test, if not an exception will be raised.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
        """
        try:
            self.driver.find_element_by_css_selector(css_selector)
            return True
        except common.exceptions.NoSuchElementException:
            return False

    def ensure_element_visible(self, css_selector=None, web_element=None):
        """
        This will ensure that an element is visible, if not an exception will be raised.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        if web_element:
            element_visible = web_element.is_displayed()
        else:
            if self.element_exists(css_selector):
                element_visible = self.driver.find_element_by_css_selector(css_selector).is_displayed()
            else:
                message = f"Element {css_selector!r} does not exist on page {self.driver.current_url!r}."
                raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                                   current_url=self.driver.current_url, css_selector=css_selector)
        if not element_visible:
            message = f"The element is not visible on page {self.driver.current_url!r}. | CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementNotVisibleError(msg=message, stacktrace=traceback.format_exc(),
                                         current_url=self.driver.current_url, css_selector=css_selector)
        else:
            return element_visible

    def get_element(self, css_selector):
        """
        Find a specific element on the page using a css_selector.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
        :return
            -   web_element:    object - The WebElement object that has been found.
        """
        try:
            web_element = self.driver.find_element_by_css_selector(css_selector)
            return web_element
        except common.exceptions.NoSuchElementException as no_such:
            message = f"Element {css_selector!r} does not exist on page {self.driver.current_url} and could not be returned.\n{no_such}"
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)
        except Exception as unexpected_error:
            message = f"Unable to find and return the element {css_selector!r} on page {self.driver.current_url!r}.\n{unexpected_error}"
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_list_of_elements(self, css_selector):
        """
        Return a full list of elements from a drop down menu, checkboxes, radio buttons, etc.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
        :return
            -   list_of_elements:   list - The full list of web elements from a parent selector (e.g. drop down menus)
        """
        if self.element_exists(css_selector):
            list_of_elements = self.driver.find_elements_by_css_selector(css_selector)
            return list_of_elements
        else:
            message = f"Element {css_selector!r} does not exist on page {(self.driver.current_url)!r}."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def wait_for_element(self, css_selector, wait_time=15, visible=False):
        """
        This will wait for a specific element to be present on the page within a specified amount of time, in seconds.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   wait_time:      integer - The amount of time, in seconds, given to wait for an element to be present.
            -   visible:        boolean - If true, wait for the element to be visible on the page; present otherwise
        """
        try:
            if visible:
                # Wait for element to be visible on the page
                WebDriverWait(
                    self.driver, wait_time).until(expected_condition.visibility_of_element_located((By.CSS_SELECTOR,
                                                                                                    css_selector)))
            else:
                # Wait for element to be present on the page
                WebDriverWait(
                    self.driver, wait_time).until(expected_condition.presence_of_element_located((By.CSS_SELECTOR,
                                                                                                  css_selector)))
        except common.exceptions.TimeoutException as timeout:
            message = f"Element {css_selector!r} does not exist on page {(self.driver.current_url)!r} after waiting {wait_time} seconds.\n{timeout}"
            raise TimeoutError(msg=message, stacktrace=traceback.format_exc(), current_url=self.driver.current_url,
                               css_selector=css_selector, wait_time=wait_time)

    def click_an_element(self, css_selector=None, web_element=None):
        """
        This will click an element on a page.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            web_element.click()
        except SeleniumHelperExceptions as click_error:
            click_error.msg = f"Unable to click element. | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise click_error
        except Exception as unexpected_error:
            message = f"An unexpected error occurred attempting to click the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"

            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def click_element_with_offset(self, css_selector=None, web_element=None, x_position=0, y_position=0):
        """
        Click an element with an offset. The offset is relative to the top-left corner of the specified element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   y_position: integer - The position at which the mouse will be placed vertically.
            -   x_position: integer - The position at which the mouse will be placed horizontally.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            ActionChains(self.driver).move_to_element_with_offset(web_element, x_position, y_position).click().perform()
        except SeleniumHelperExceptions as click_location_error:
            click_location_error.msg = f"Unable to click the position ({x_position}, {y_position}). | Based off the CSS Selector: {css_selector!r} or WebElement passed through. | " + click_location_error.msg
            raise click_location_error
        except Exception as unexpected_error:
            message = f"Unable to click at the position ({x_position}, {y_position}) of the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ClickPositionError(msg=message, stacktrace=traceback.format_exc(),
                                     current_url=self.driver.current_url, css_selector=css_selector,
                                     y_position=y_position, x_position=x_position)

    def double_click(self, css_selector=None, web_element=None):
        """
        Double click an element on the page.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            ActionChains(self.driver).double_click(web_element).perform()
        except SeleniumHelperExceptions as double_click_error:
            double_click_error.msg = "Unable to double click element. | " + double_click_error.msg
            raise double_click_error
        except Exception as unexpected_error:
            message = f"Unable to double-click the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def move_cursor_to_location(self, x_position=0, y_position=0, click=False):
        """
        Move the cursor to a specific location on the page. This will first move the cursor to (0,0) on the page and
        then move to the coordinates the user passes in. There is an option to click after the cursors moves to the
        specified coordinates.
        :param
            -   y_position: integer - The position at which the mouse will be placed vertically.
            -   x_position: integer - The position at which the mouse will be placed horizontally.
            -   click: boolean - Whether or not a click will be performed after the the cursor is moved.
        """
        try:
            # Starting the cursor off at the absolute (0,0) point on the page.
            web_element = self.get_element("body")
            ActionChains(self.driver).move_to_element_with_offset(web_element, 0, 0).perform()
            if click:
                # Moving the cursor to and clicking the specified coordinates provided.
                ActionChains(self.driver).move_by_offset(x_position, y_position).click().perform()
            else:
                # Moving the cursor to the specified coordinates provided.
                ActionChains(self.driver).move_by_offset(x_position, y_position).perform()
        except Exception as unexpected_error:
            message = f"Unable to move the cursor to ({x_position},{y_position}) on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            raise CursorLocationError(msg=message, stacktrace=traceback.format_exc(),
                                      current_url=self.driver.current_url, x_position=x_position, y_position=y_position)

    def clear_an_element(self, css_selector=None, web_element=None):
        """
        This will clear a field on a page.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.click_an_element(web_element=web_element, css_selector=css_selector)
            web_element.clear()
        except SeleniumHelperExceptions as clear_error:
            clear_error.msg = "Unable to clear element. | " + clear_error.msg
            raise clear_error
        except Exception as unexpected_error:
            message = f"Unable to clear the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def fill_an_element(self, fill_text, css_selector=None, web_element=None):
        """
        This will fill a field on a page.
        :param
            -   fill_text:  string - The text that will be sent through to a field on page.
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.clear_an_element(web_element=web_element, css_selector=css_selector)
            web_element.send_keys(fill_text)
        except SeleniumHelperExceptions as fill_error:
            fill_error.msg = "Unable to fill element. | " + fill_error.msg
            raise fill_error
        except Exception as unexpected_error:
            message = f"Unable to fill the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def send_special_key(self, special_key):
        """
        This will send a special key through to the driver (e.g. TAB, ENTER, RETURN).
        :param
            -   special_key:  string - The key that will be sent through to the driver.
        """
        try:
            ActionChains(self.driver).send_keys(getattr(Keys, special_key.upper())).perform()
        except Exception as send_special_key_error:
            message = f"Unable to send the special key {special_key!r}.\n{send_special_key_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def hover_on_element(self, css_selector=None, web_element=None):
        """
        This will hover over an element on a page.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            hover = ActionChains(self.driver).move_to_element(web_element)
            hover.perform()
        except SeleniumHelperExceptions as hover_error:
            hover_error.msg = "Unable to hover over element. | " + hover_error.msg
            raise hover_error
        except Exception as unexpected_error:
            message = f"Unable to hover over the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def execute_script(self, script, *script_arguments):
        """
        This will run JavaScript through the browser.
        :param
            -   script: string - JavaScript to be sent through to browser.
            -   argument: list - Arguments to be used in the script that is sent to the browser.
        :return
            -   script: string, int - Any value that the script could return for future consumption.
        """
        try:
            if script_arguments:
                # Execute the script with a specific WebElement.
                return self.driver.execute_script(script, *script_arguments)
            else:
                # Execute the script without a specific WebElement.
                return self.driver.execute_script(script)
        except Exception as unexpected_error:
            message = f"Unable to execute given script on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def scroll_to_element(self, css_selector=None, web_element=None, position_bottom=False, position_middle=False,
                          offset=0):
        """
        This will scroll to an element on a page. This element can be put at the top, the bottom, or the middle
        (or close to) of the page.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   position_top:   boolean - Whether or not the element will be at the top of the page.
            -   position_bottom:    boolean - Whether or not the element will be at the bottom of the page.
            -   position_middle:    boolean - Whether or not the element will be in the middle of the page.
            -   offset:    integer - The amount above or below of the element you'd like to scroll
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)

            if offset:
                y_pos = self.get_element_location(web_element=web_element)
                scroll_position = y_pos + offset
                self.execute_script("window.scrollTo(0, arguments[0]);", scroll_position)
            elif position_bottom:
                # Scroll the window so the bottom of the element will be at the bottom of the window.
                self.execute_script("var element = arguments[0]; element.scrollIntoView(false);",
                                    web_element)
            elif position_middle:
                # Find the scroll position of the top of the element
                element_position = self.execute_script("var element = arguments[0]; "
                                                       "var height = element.offsetTop; "
                                                       "return height", web_element)
                # Determine the position that is half a screen height above the element
                screen_padding = (self.driver.get_window_size()["height"] / 2)
                scroll_position = element_position - screen_padding
                # Scroll to that position
                self.execute_script("window.scrollTo(0, arguments[0]);", scroll_position)
            else:
                # Scroll the window so the top of the element will be at the top of the window.
                self.execute_script("var element = arguments[0]; element.scrollIntoView(true);",
                                    web_element)

        except SeleniumHelperExceptions as scroll_to_element_error:
            scroll_to_element_error.msg = "Unable to scroll to element. | " + scroll_to_element_error.msg
            raise scroll_to_element_error
        except Exception as unexpected_error:
            message = f"Unable to scroll to the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def scroll_window_to_position(self, y_position=0, x_position=0, scroll_top=False, scroll_bottom=False):
        """
        This will scroll to a specific position on the current page, scroll to the top of the page, or it will scroll
        to the bottom of the page.
        :param
            -   y_position: integer - The position the browser will scroll to vertically.
            -   x_position: integer - The position the browser will scroll to horizontally.
            -   scroll_top: boolean - Whether or not the element will be scrolled to the top.
            -   scroll_bottom:  boolean - Whether or not the element will be scrolled to the bottom.
        """
        try:
            if scroll_top:
                self.execute_script("window.scrollTo(0, 0);")
            elif scroll_bottom:
                total_height = self.execute_script("var height = document.body.scrollHeight; return height")
                self.execute_script("window.scrollTo(0, arguments[0]);", total_height)
            elif type(y_position) == int or type(x_position) == int:
                self.execute_script("window.scrollTo(arguments[0], arguments[1]);", x_position, y_position)
            else:
                message = f"Unable to scroll to position ({x_position!r}, {y_position!r}) on page {(self.driver.current_url)!r}."
                raise ScrollPositionError(msg=message, stacktrace=traceback.format_exc(),
                                          current_url=self.driver.current_url, y_position=y_position,
                                          x_position=x_position)
        except Exception as scroll_window_to_position_error:
            message = f"Unable to scroll to position ({x_position!r}, {y_position!r}).\n{scroll_window_to_position_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def get_window_current_scroll_position(self, get_both_positions=False, get_only_x_position=False):
        """
        This will get the current scroll position that the window is at. You can get both the X scroll position and Y
        scroll position, only the X scroll position, or only the Y scroll position.
        :param
            -   get_both_positions: boolean - Whether or not both the X position and Y position are returned.
            -   get_only_x_position: boolean - Whether or not only the X position is returned.
        :return
            -   x_scroll_position:  integer - The amount that the window has been scrolled on the x axis.
            -   y_scroll_position:  integer - The amount that the window has been scrolled on the y axis.
        """
        try:
            x_scroll_position = self.execute_script("return window.scrollX;")
            y_scroll_position = self.execute_script("return window.scrollY;")
            if get_both_positions and not get_only_x_position:
                return x_scroll_position, y_scroll_position
            elif get_only_x_position and not get_both_positions:
                return x_scroll_position
            else:
                return y_scroll_position
        except Exception as get_window_current_scroll_position_error:
            message = f"Unable to determine the scroll position of the window.\n{get_window_current_scroll_position_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def scroll_an_element(self, css_selector=None, web_element=None, y_position=0, x_position=0, scroll_padding=0,
                          scroll_top=False, scroll_bottom=False, scroll_left=False, scroll_right=False,
                          scroll_horizontal=False):
        """
        This will scroll an element on a page (e.g. An ISI modal).  The user can have it scroll to the top of the
        element, the bottom of the element, a specific position in the element, or by the height of the scrollable area
        of the element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   y_position:    integer - The position that the element will be scrolled to vertically.
            -   x_position:    integer - The position that the element will be scrolled to horizontally.
            -   scroll_padding: integer - The amount of padding that will be used when scroll by the element's height.
            -   scroll_top: boolean - Whether or not the element will be scrolled to the top.
            -   scroll_bottom:  boolean - Whether or not the element will be scrolled to the bottom.
            -   scroll_left:  boolean - Whether or not the element will be scrolled to the left.
            -   scroll_right:  boolean - Whether or not the element will be scrolled to the right.
            -   scroll_horizontal:  boolean - Whether or not the element will be scrolled to the horizontally.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            if scroll_top:
                self.execute_script("arguments[0].scrollTop = 0;", web_element)
            elif scroll_bottom:
                element_max_height = self.execute_script("var element = arguments[0]; "
                                                         "var scrollHeight = element.scrollHeight; "
                                                         "var clientHeight = element.clientHeight; "
                                                         "var maxHeight = scrollHeight - clientHeight; "
                                                         "return maxHeight;", web_element)
                self.execute_script("arguments[0].scrollTop = arguments[1];", web_element, element_max_height)
            elif scroll_left:
                self.execute_script("arguments[0].scrollLeft = 0;", web_element)
            elif scroll_right:
                element_max_width = self.execute_script("var element = arguments[0]; "
                                                        "var scrollWidth = element.scrollWidth; "
                                                        "var clientWidth = element.clientWidth; "
                                                        "var maxWidth = scrollWidth - clientWidth; "
                                                        "return maxWidth;", web_element)
                self.execute_script("arguments[0].scrollLeft = arguments[1];", web_element, element_max_width)
            elif y_position or x_position:
                self.execute_script("arguments[0].scrollTop = arguments[1];", web_element, y_position)
                self.execute_script("arguments[0].scrollLeft = arguments[1];", web_element, x_position)
            elif scroll_horizontal:
                element_width = self.execute_script("var element = arguments[0]; "
                                                    "var elementWidth = element.offsetWidth; "
                                                    "return elementWidth;", web_element)
                self.execute_script("arguments[0].scrollLeft += (arguments[1] - arguments[2]);",
                                    web_element, element_width, scroll_padding)
            else:
                element_height = self.execute_script("var element = arguments[0]; "
                                                     "var elementHeight = element.offsetHeight; "
                                                     "return elementHeight;", web_element)
                self.execute_script("arguments[0].scrollTop += (arguments[1] - arguments[2]);",
                                    web_element, element_height, scroll_padding)
        except SeleniumHelperExceptions as scroll_element_error:
            scroll_element_error.msg = "Unable to scroll element. | " + scroll_element_error.msg
            raise scroll_element_error
        except Exception as unexpected_error:
            message = f"Unable to scroll the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_element_current_scroll_position(self, css_selector=None, web_element=None, get_both_positions=False,
                                            get_only_x_position=False):
        """
        Check to see what position the scrollable element is at.You can get both the X scroll position and Y
        scroll position, only the X scroll position, or only the Y scroll position.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   get_both_positions: boolean - Whether or not both the X position and Y position are returned.
            -   get_only_x_position:    boolean - Whether or not only the X position is returned.
        :return
            -   x_scroll_position:  integer - The amount that the element has been scrolled on the x axis.
            -   y_scroll_position:  integer - The amount that the element has been scrolled on the y axis.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            x_scroll_position = self.execute_script("var element = arguments[0]; "
                                                    "scrollPosition = element.scrollLeft; "
                                                    "return scrollPosition;", web_element)
            y_scroll_position = self.execute_script("var element = arguments[0]; "
                                                    "scrollPosition = element.scrollTop; "
                                                    "return scrollPosition;", web_element)
            if get_both_positions and not get_only_x_position:
                return x_scroll_position, y_scroll_position
            elif get_only_x_position and not get_both_positions:
                return x_scroll_position
            else:
                return y_scroll_position
        except SeleniumHelperExceptions as current_scroll_error:
            current_scroll_error.msg = "Unable to determine the element's scroll position. | " + current_scroll_error.msg
            raise current_scroll_error
        except Exception as unexpected_error:
            message = f"Unable to determine the scroll position of the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_is_element_scroll_position_at_top(self, css_selector=None, web_element=None):
        """
        Check to see if the scroll position is at the top of the scrollable element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        :return
            -   at_top: boolean - Whether or not the scrollable element is at the top.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            scroll_position = self.execute_script("var element = arguments[0]; "
                                                  "scrollPosition = element.scrollTop; "
                                                  "return scrollPosition;", web_element)
            if scroll_position != 0:
                return False
            else:
                return True
        except SeleniumHelperExceptions as scroll_at_top_error:
            scroll_at_top_error.msg = "Unable to determine if element is scrolled to the top. | " + scroll_at_top_error.msg
            raise scroll_at_top_error
        except Exception as unexpected_error:
            message = f"Unable to determine if the scroll position of the element on page {(self.driver.current_url)!r} is at the top.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_is_element_scroll_position_at_bottom(self, css_selector=None, web_element=None):
        """
        Check to see if the scroll position is at the bottom of the scrollable element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        :return
            -   at_bottom:  boolean - Whether or not the scrollable element is at the bottom.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            element_max_height = self.execute_script("var element = arguments[0]; "
                                                     "var scrollHeight = element.scrollHeight; "
                                                     "var clientHeight = element.clientHeight; "
                                                     "var maxHeight = scrollHeight - clientHeight; "
                                                     "return maxHeight;", web_element)
            scroll_position = self.execute_script("var element = arguments[0]; "
                                                  "var scrollPosition = element.scrollTop; "
                                                  "return scrollPosition;", web_element)
            if scroll_position < element_max_height - 1:
                return False
            else:
                return True
        except SeleniumHelperExceptions as scroll_at_bottom_error:
            scroll_at_bottom_error.msg = "Unable to determine if element is scrolled to the bottom. | " + scroll_at_bottom_error.msg
            raise scroll_at_bottom_error
        except Exception as unexpected_error:
            message = f"Unable to determine if the scroll position of the element on page {(self.driver.current_url)!r} is at the bottom.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_is_element_scroll_position_at_most_right(self, css_selector=None, web_element=None):
        """
        Check to see if the scroll position is at the most right of the scrollable element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        :return
            -   at_right:  boolean - Whether or not the scrollable element is at the most right.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            element_max_width = self.execute_script("var element = arguments[0]; "
                                                    "var scrollWidth = element.scrollWidth; "
                                                    "var clientWidth = element.clientWidth; "
                                                    "var maxWidth = scrollWidth - clientWidth; "
                                                    "return maxWidth;", web_element)
            scroll_position = self.execute_script("var element = arguments[0]; "
                                                  "var scrollPosition = element.scrollLeft; "
                                                  "return scrollPosition;", web_element)
            if scroll_position < element_max_width - 1:
                return False
            else:
                return True
        except SeleniumHelperExceptions as scroll_at_right_error:
            scroll_at_right_error.msg = "Unable to determine if element is scrolled to the most right. | " + scroll_at_right_error.msg
            raise scroll_at_right_error
        except Exception as unexpected_error:
            message = f"Unable to determine if the scroll position of the element on page {(self.driver.current_url)!r} is at the most right.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_element_size(self, css_selector=None, web_element=None, get_width_and_height=False, get_only_width=False):
        """
        This will get the current size of an element. You can get both the width and height, only the width, 
        or only the height.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   get_width_and_height: boolean - Whether or not both the width and the height are returned.
            -   get_only_width: boolean - Whether or not only the width is returned.
        :return
            -   width:  integer - The width of the element.
            -   height: integer - The height of the element.
        """
        try:
            if css_selector and not web_element:
                self.element_exists(css_selector)
                web_element = self.get_element(css_selector)

            size = web_element.size
            width = size["width"]
            height = size["height"]

            if get_width_and_height and not get_only_width:
                return width, height
            elif get_only_width and not get_width_and_height:
                return width
            else:
                return height
        except SeleniumHelperExceptions as selenium_error:
            selenium_error.msg = f"Unable to get the size of the element. | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise selenium_error
        except Exception as unexpected_error:
            message = f"An unexpected error occurred attempting to get the size of the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"

            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def get_element_location(self, css_selector=None, web_element=None, get_both_positions=False,
                             get_only_x_position=False):
        """
        This will get the location of the element on the page. You can get both the X position and Y position, 
        only the X position, or only the Y position.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
            -   get_both_positions: boolean - Whether or not both the X position and Y position are returned.
            -   get_only_x_position: boolean - Whether or not only the X position is returned.
        :return
            -   x_position:  integer - The element's location on the x axis.
            -   y_position:  integer - The element's location on the y axis.
        """
        try:
            if css_selector and not web_element:
                self.element_exists(css_selector=css_selector)
                web_element = self.get_element(css_selector)

            location = web_element.location
            x_position = location["x"]
            y_position = location["y"]
            if get_both_positions and not get_only_x_position:
                return x_position, y_position
            elif get_only_x_position and not get_both_positions:
                return x_position
            else:
                return y_position
        except SeleniumHelperExceptions as selenium_error:
            selenium_error.msg = f"Unable to get the location of the element. | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise selenium_error
        except Exception as unexpected_error:
            message = f"An unexpected error occurred attempting to get the location of the element on page {(self.driver.current_url)!r}.\n{unexpected_error}"

            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def hide_element(self, css_selector=None, web_element=None):
        """
        This will hide a specified element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.ensure_element_visible(web_element=web_element, css_selector=css_selector)
            self.execute_script("arguments[0].style.display = 'none';", web_element)
        except SeleniumHelperExceptions as hide_error:
            hide_error.msg = "Unable to hide element. | " + hide_error.msg
            raise hide_error
        except Exception as unexpected_error:
            message = f"Unable to hide element on page {(self.driver.current_url)!r}, it may already hidden.\n{unexpected_error}"
            message += f" | Based off the CSS Selector: {css_selector!r} or WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def show_element(self, css_selector=None, web_element=None):
        """
        This will show a specified element.
        :param
            -   css_selector:   string - The specific element that will be interacted with.
            -   web_element:    object - The WebElement that will be interacted with.
        """
        try:
            if css_selector and not web_element:
                web_element = self.get_element(css_selector)
            self.execute_script("arguments[0].style.display = 'block';", web_element)
        except SeleniumHelperExceptions as show_error:
            show_error.msg = "Unable to show element. | " + show_error.msg
            raise show_error
        except Exception as unexpected_error:
            message = f"Unable to show element on page {(self.driver.current_url)!r}, that element may not exist.\n{unexpected_error}"
            if css_selector:
                message += f" | CSS Selector: {css_selector!r}"
            else:
                message += " | Based off the WebElement passed through."
            raise ElementError(msg=message, stacktrace=traceback.format_exc(),
                               current_url=self.driver.current_url, css_selector=css_selector)

    def add_cookie(self, name=None, value=None):
        """
            This will show a specified element.
            :param
                -   name:   string - Name of the cookie you want to pass in .
                -   value:    string - Valye of the cookie.
       """
        try:
            url = self.get_current_url()
            url_parse = urlparse(url)
            domain = f".{((url_parse.netloc.split('.', 1)[-1]))}"
            path = url_parse.path
            self.driver.add_cookie({"name": name, "value": value, "domain": domain, "path": path})
        except Exception as cookie_error:
            message = f"There was an issue creating a a cookie: {cookie_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())

    def delete_cookie(self, name=None):
        """
            This will show a specified element.
            :param
                -   name:   string - Name of the cookie you want to delete .
       """
        try:
            self.driver.delete_cookie(name)
        except Exception as cookie_error:
            message = f"There was an issue deleting a a cookie: {cookie_error}"
            raise DriverAttributeError(msg=message, stacktrace=traceback.format_exc())


class SeleniumHelperExceptions(common.exceptions.WebDriverException):
    def __init__(self, msg, stacktrace, current_url):
        self.current_url = current_url
        self.details = {"current_url": self.current_url, "stacktrace": stacktrace}
        super(SeleniumHelperExceptions, self).__init__(msg=msg, stacktrace=stacktrace)

    def __str__(self):
        exception_msg = "Selenium Exception: \n"
        detail_string = "Exception Details:\n"
        for key, value in self.details.items():
            detail_string += f"{key}: {value}\n"
        exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg


class ElementError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, css_selector):
        super(ElementError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.css_selector = css_selector
        self.details["css_selector"] = self.css_selector


class ElementNotVisibleError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, css_selector):
        super(ElementNotVisibleError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.css_selector = css_selector
        self.details["css_selector"] = self.css_selector


class TimeoutError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, css_selector, wait_time):
        super(TimeoutError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.css_selector = css_selector
        self.wait_time = wait_time
        self.details["css_selector"] = self.css_selector
        self.details["wait_time"] = self.wait_time


class ClickPositionError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, css_selector, y_position, x_position):
        super(ClickPositionError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.css_selector = css_selector
        self.y_position = y_position
        self.x_position = x_position
        self.details["css_selector"] = self.css_selector
        self.details["y_position"] = self.y_position
        self.details["x_position"] = self.x_position


class CursorLocationError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, x_position, y_position):
        super(CursorLocationError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.x_position = x_position
        self.y_position = y_position
        self.details["x_position"] = self.x_position
        self.details["y_position"] = self.y_position


class ScrollPositionError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, y_position, x_position):
        super(ScrollPositionError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.y_position = y_position
        self.x_position = x_position
        self.details["y_position"] = self.y_position
        self.details["x_position"] = self.x_position


class ScreenshotError(SeleniumHelperExceptions):
    def __init__(self, msg, stacktrace, current_url, file_name, file_path):
        super(ScreenshotError, self).__init__(msg=msg, stacktrace=stacktrace, current_url=current_url)
        self.file_name = file_name
        self.file_path = file_path
        self.details["file_name"] = self.file_name
        self.details["file_path"] = self.file_path


class DriverExceptions(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(DriverExceptions, self).__init__()

    def __str__(self):
        exception_msg = "Driver Creation Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"\nStacktrace: {self.stacktrace}\n"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg


class DriverAttributeError(DriverExceptions):
    def __init__(self, msg, stacktrace=None):
        super(DriverAttributeError, self).__init__(msg=msg, stacktrace=stacktrace)


class DriverSizeError(DriverExceptions):
    def __init__(self, msg, stacktrace=None, width=None, height=None):
        super(DriverSizeError, self).__init__(msg=msg, stacktrace=stacktrace)
        self.width = width
        self.height = height
        self.details["width"] = self.width
        self.details["height"] = self.height


class DriverURLError(DriverExceptions):
    def __init__(self, msg, stacktrace=None, desired_url=None):
        super(DriverURLError, self).__init__(msg=msg, stacktrace=stacktrace)
        self.desired_url = desired_url
        self.details["desired_url"] = self.desired_url
