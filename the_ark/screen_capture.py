import numpy
from PIL import Image
from the_ark.selenium_helpers import SeleniumHelperExceptions, ElementNotVisibleError, ElementError
from StringIO import StringIO
import time
import traceback

DEFAULT_SCROLL_PADDING = 100
SCREENSHOT_FILE_EXTENSION = "png"
DEFAULT_PIXEL_MATCH_OFFSET = 100


class Screenshot:
    """
    A helper class for taking screenshots using a Selenium Helper instance
    """
    def __init__(self, selenium_helper, paginated=False, header_ids=None, footer_ids=None,
                 scroll_padding=DEFAULT_SCROLL_PADDING, pixel_match_offset=DEFAULT_PIXEL_MATCH_OFFSET,
                 file_extenson=SCREENSHOT_FILE_EXTENSION):
        """
        Initializes the Screenshot class. These variable will be used throughout to help determine how to capture pages
        for this website.
        :param
            - selenium_helper:  SeleniumHelper() - The Selenium Helper object whose browser you are capturing
            - paginated:        bool - if True, all full page screenshots captured by this class will be a sequence of
                                    viewport sized images
            - header_ids:       list - A list of css_selectors for elements that "stick" to the top of the screen when
                                    scrolling. These hidden and shown while capturing the screen so that they display
                                    only at the top of the page, and do not cover any content
            - footer_ids:       list - A list of css_selectors for elements that "stick" to the bottom of the screen
                                    when scrolling. These hidden and shown while capturing the screen so that they
                                    display  only at the bottom of the page, and do not cover any content
            - scroll_padding:   int - The height, in pixels, of the overlap between paginated captures. This is also
                                    used when scrolling elements. the element is scrolled its height minus the padding
                                    to create an overlapping of content shown on both images to not cut any text in half
            - file_extenson:    string - If provided, this extension will be used while creating the image. This must
                                        be an extension that is usable with PIL
        """
        # Set parameters as class variables
        self.sh = selenium_helper
        self.paginated = paginated
        self.headers = header_ids
        self.footers = footer_ids
        self.scroll_padding = scroll_padding
        self.pixel_match_offset = pixel_match_offset
        self.file_extenson = file_extenson

    def capture_page(self, viewport_only=False, padding=None):
        """
        Entry point for a screenshot of the whole page. This will send the screenshot off to the correct methods
        depending on whether you need paginated screenshots, just the current viewport area, or the whole page in
        one large shot.
        :param
            - viewport_only:  bool - Whether to capture just the viewport's visible area or not
        :return
            - StringIO: A StingIO object containing the captured image(s)
        """
        try:
            if viewport_only:
                return self._capture_single_viewport()
            elif self.paginated:
                return self._capture_paginated_page(padding)
            else:
                return self._capture_full_page()

        except SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while taking the screenshot".format()
            error = SeleniumError(message, selenium_error)
            raise error
        except Exception as e:
            message = "Unhandled exception while taking the screenshot | {0}".format(e)
            raise ScreenshotException(message, stacktrace=traceback.format_exc())

    def capture_scrolling_element(self, css_selector, viewport_only=True, scroll_padding=None):
        """
        This method will scroll an element one height (with padding) and take a screenshot each scroll until the element
        has been scrolled to the bottom. You can choose to capture the whole page (helpful when the scrollable element
        is taller than the viewport) or just the viewport area
        :param
            - css_selector:     string - The css selector for the element that you plan to scroll
            - viewport_only:    bool   - Whether to capture just the viewport's visible area or not (each screenshot
                                       after scrolling)
            - scroll_padding:   int    - Overwrites the default scroll padding for the class. This can be used when the
                                       element, or site, have greatly different scroll padding numbers
        :return
            - StringIO:     list - A list containing multiple StringIO image objects
        """
        padding = scroll_padding if scroll_padding else self.scroll_padding

        try:
            image_list = []
            # Scroll the element to the top
            self.sh.scroll_an_element(css_selector, scroll_top=True)

            while True:
                # Capture the image
                if viewport_only:
                    image_list.append(self._capture_single_viewport())
                else:
                    image_list.append(self._capture_full_page())

                if self.sh.get_is_element_scroll_position_at_bottom(css_selector):
                    # Stop capturing once you're at the bottom
                    break
                else:
                    # Scroll down for the next one!
                    self.sh.scroll_an_element(css_selector, scroll_padding=padding)

            return image_list

        except SeleniumHelperExceptions as selenium_error:
            message = "A selenium issue arose while trying to capture the scrolling element"
            error = SeleniumError(message, selenium_error)
            raise error
        except Exception as e:
            message = "Unhandled exception while taking the scrolling screenshot " \
                      "of the element '{0}' | {1}".format(css_selector, e)
            raise ScreenshotException(message,
                                      stacktrace=traceback.format_exc(),
                                      details={"css_selector": css_selector})

    def _capture_single_viewport(self):
        """
        Grabs an image of the page and then craps it to just the visible / viewport area
        :return
            - StringIO: A StingIO object containing the captured image
        """
        cropped_image = self._get_image_data(viewport_only=True)
        return self._create_image_file(cropped_image)

    def _capture_full_page(self):
        """
        Captures an image of the whole page. If there are sitcky elements, as specified by the footers and headers
        class variables the code will, the code will capture them only where appropriate ie. headers on top, footers on
        bottom. Otherwise the whole screen is sent back as it is currently set up.
        :return
            - StringIO: A StingIO object containing the captured image
        """
        if self.headers and self.footers:
            # Capture viewport size window of the headers
            self.sh.scroll_window_to_position(0)
            self._hide_elements(self.footers)
            header_image = self._get_image_data(True)

            # - Capture the page from the bottom without headers
            self._show_elements(self.footers)
            #TODO: Update when scroll position updates to have a scroll to bottom option
            self.sh.scroll_window_to_position(40000)
            self._hide_elements(self.headers)
            footer_image = self._get_image_data()

            # Show all header elements again
            self._show_elements(self.headers)

            # Send the two images off to get merged into one
            image_data = self._crop_and_stitch_image(header_image, footer_image)
        elif self.headers:
            # Scroll to the top so that the headers are not covering content
            self.sh.scroll_window_to_position(0)
            time.sleep(0.5)
            image_data = self._get_image_data()
        elif self.footers:
            # Scroll to the bottom so that the footer items are not covering content
            self.sh.scroll_window_to_position(40000)
            time.sleep(0.5)
            image_data = self._get_image_data()
        else:
            image_data = self._get_image_data()

        return self._create_image_file(image_data)

    def _hide_elements(self, css_selectors):
        """
        Hides all elements in the given list
        :param
            - css_selectors:    list - A list of the elements you would like to hide
        """
        for selector in css_selectors:
            try:
                self.sh.hide_element(selector)
            # Continue to the next item is this one did not exist or was already not visible
            except ElementNotVisibleError:
                pass
            except ElementError:
                pass

    def _show_elements(self, css_selectors):
        """
        Shows all elements in the given list
        :param
            - css_selectors:    list - A list of the elements you would like to make visible
        """
        # Show footer items again
        for selector in css_selectors:
            try:
                self.sh.show_element(selector)
            # Continue to the next item is this one did not exist
            except ElementError:
                pass

    def _capture_paginated_page(self, padding=None):
        """
        Captures the page viewport by viewport, leaving an overlap of pixels the height of the self.padding variable
        between each image
        """
        image_list = []
        scroll_padding = padding if padding else self.scroll_padding

        # Scroll page to the top
        self.sh.scroll_window_to_position(0)

        current_scroll_position = 0
        viewport_height = self.sh.driver.execute_script("return document.documentElement.clientHeight")

        while True:
            # Capture the image
            image_list.append(self._capture_single_viewport())

            # Scroll for the next one!
            self.sh.scroll_window_to_position(current_scroll_position + viewport_height - scroll_padding)
            time.sleep(0.25)
            new_scroll_position = self.sh.get_window_current_scroll_position()

            # Break if the scroll position did not change (because it was at the bottom)
            if new_scroll_position == current_scroll_position:
                break
            else:
                current_scroll_position = new_scroll_position

        return image_list

    def _get_image_data(self, viewport_only=False):
        """
        Creates an Image() canvas of the page. The image is cropped to be only the viewport area if specified.
        :param
            - viewport_only:    bool - Captures only the visible /viewport area if true

        :return
            - image:    Image() - The image canvas of the captured data
        """
        # - Capture the image
        # Gather image byte data
        image_data = self.sh.get_screenshot_base64()
        # Create an image canvas and write the byte data to it
        image = Image.open(StringIO(image_data.decode('base64')))

        if self.sh.desired_capabilities.get("mobile"):
            return image
        elif viewport_only:
            # - Crop the image to just the visible area
            # Top of the viewport
            current_scroll_position = self.sh.get_window_current_scroll_position()

            # Viewport Dimensions
            viewport_width, viewport_height = self.sh.get_viewport_size()

            # Calculate the visible area
            crop_box = (0, current_scroll_position, viewport_width, current_scroll_position + viewport_height)

            # Crop everything of the image but the visible area
            cropped_image = image.crop(crop_box)
            return cropped_image
        else:
            return image

    def _crop_and_stitch_image(self, header_image, footer_image):
        """
        This object takes in a header and footer image. It then searched for a block of 100 mixles that matches between
        the two images. Once it finds this point the footer image is cropped above the "match" point. A new canvas is
        then created that is the total height of both images. The two images are then copied onto a new canvas to create
        the final image, headers on top, footers on the bottom.
        :param
            - header_image:     Image() - The top of the page, usually displays all of the headers elements
            - footer_image:     Image() - The bottom of the page, usually displays all of the footer elements
        :return
            - stitched_image:   Image() - The resulting image of the crop and stitching of the header and footer images
        """
        try:
            # Create Pixel Row arrays from each image
            header_array = numpy.asarray(header_image)
            footer_array = numpy.asarray(footer_image)

            # - Find a place in both images that match then crop and stitch them at that location
            crop_row = 0
            header_image_height = header_image.height
            # Set the offset to the height of the image if the height is less than the offset
            if self.pixel_match_offset > header_image_height:
                self.pixel_match_offset = header_image_height

            # - Find the pixel row in the footer image that matches the bottom row in the header image
            # Grab the last 100 rows of header_image
            header_last_hundred_rows = header_array[header_image_height - self.pixel_match_offset: header_image_height]

            # Iterates throughout the check, will match the height of the row being checked in the image.
            for i, footer_row in enumerate(footer_array):
                # Jump out if the crop row has been set
                if crop_row != 0:
                    break

                # Check if the current row being inspected matches the header row 100 pixels above the bottom
                if numpy.array_equal(footer_row, header_last_hundred_rows[0]):
                    # It is a match!
                    for y, row in enumerate(header_last_hundred_rows):
                        # Check that the 100 footer rows above the matching row also match the bottom 100 of
                        # the header image we grabbed at the start of this check
                        if numpy.array_equal(footer_array[i + y], header_last_hundred_rows[y]):
                            # Check whether we've found 100 matching rows or not
                            if y == self.pixel_match_offset - 1:
                                # Yes! All 100 matched. Set the crop row to this row
                                crop_row = i + self.pixel_match_offset
                                break

            # If no rows matched, crop at height of header image
            if crop_row == 0:
                crop_row = header_image_height

            # - Crop the top of the footer image off above the line that matches the header image's bottom row
            # Create the crop box that outlines what to remove from the footer image
            footer_image_width = footer_image.size[0]
            footer_image_height = footer_image.size[1]
            crop_box = (0, crop_row, footer_image_width, footer_image_height)
            # Perform the crop
            cropped_footer_image = footer_image.crop(crop_box)

            # Grab the new height of the footer image
            cropped_footer_image_height = cropped_footer_image.size[1]

            # Create a blank image canvas that is as tall the footer and header images combined
            total_height = header_image_height + cropped_footer_image_height
            stitched_image = Image.new("RGB", (footer_image_width, total_height))

            # - Paste the header and footer images onto the canvas
            # Paste the header image at the top
            stitched_image.paste(header_image, (0, 0))
            # Paste the footer image directly below the header image
            stitched_image.paste(cropped_footer_image, (0, header_image_height))

            return stitched_image

        except Exception as e:
            message = "Error while cropping and stitching a full page screenshot | {0}".format(e)
            raise ScreenshotException(message, stacktrace=traceback.format_exc())

    def _create_image_file(self, image):
        """
        This method takes an Image() variable and saves it into a StringIO "file".
        :param
            - image_data:   Image() - The image to be saved into the StringIO object

        :return
            - image_file:   StingIO() - The stringIO object containing the saved image
        """
        # Instantiate the file object
        image_file = StringIO()
        # Save the image canvas to the file as the given file type
        image.save(image_file, self.file_extenson.upper())
        # Set the file marker back to the beginning
        image_file.seek(0)

        return image_file


class ScreenshotException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.details["stracktrace"] = stacktrace
        super(ScreenshotException, self).__init__()

    def __str__(self):
        exception_msg = "Screenshot Exception: \n"
        detail_string = "Exception Details:\n"
        for key, value in self.details.items():
            detail_string += "{0}: {1}\n".format(key, value)
        exception_msg += detail_string
        exception_msg += "Message: {0}".format(self.msg)

        return exception_msg


class SeleniumError(ScreenshotException):
    def __init__(self, message, selenium_helper_exception):
        new_message = "{0} | {1}".format(message, selenium_helper_exception.msg)
        super(SeleniumError, self).__init__(msg=new_message,
                                            stacktrace=selenium_helper_exception.stacktrace,
                                            details=selenium_helper_exception.details)