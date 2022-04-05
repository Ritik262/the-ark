from urllib.parse import urlparse, urlunparse
import requests
import traceback


def get_jcr_content(root_url, root_path, depth=0, infinity=False):
    """Returns the JCR content json for a given url and root path
    NOTE: Does not support authentication
    :param root_url:
        STRING fully qualified url for an aem publish instance
    :param root_path:
        STRING path to the node in the JCR
    :param depth:
        INTEGER number (positive or 0) of levels to descend from the content path. DEFAULT: 0
    :param infinity:
        BOOLEAN flag for infinite depth. If False, provided depth will be used. DEFAULT: False
    :return:
        JSON JCR content
    """
    # cleanup input strings, add protocol to url if one isn't provided
    root_path = root_path[:-5] if root_path.endswith('.html') else root_path
    root_path = f"/{root_path}" if not root_path.startswith('/') else root_path
    root_url = root_url[:-1] if root_url.endswith('/') else root_url
    if not urlparse(root_url).scheme:
        root_url = "http://" + root_url
    jcr_content_url = root_url

    try:
        parsed_url = urlparse(root_url)
        if infinity:
            jcr_content_url = f"{(urlunparse((parsed_url.scheme, parsed_url.netloc, root_path, None, None, None)))}.infinity.json"
        else:
            jcr_content_url = f"{urlunparse((parsed_url.scheme, parsed_url.netloc, root_path, None, None, None))}.{depth}.json"

        infinity_json = requests.get(jcr_content_url).json()

        return infinity_json
    except requests.RequestException as re:
        message = "A Request Exception occurred when attempting to " \
                  f"retrieve the jcr infinity JSON for url: {jcr_content_url} | " \
                  f"Exception: {re.message}"
        raise JCRHelperException(message, stacktrace=traceback.format_exc())
    except ValueError as ve:
        message = f"Unable to retrieve the jcr infinity JSON. JSON was not returned for url: {jcr_content_url} | " \
                  "Exception: {ve.message}"
        raise JCRHelperException(message, stacktrace=traceback.format_exc())
    except Exception as e:
        message = f"An unexpected error occurred when retrieving the jcr infinity JSON for url: {jcr_content_url} | " \
                  f"Exception: {e.message}"
        raise JCRHelperException(message, stacktrace=traceback.format_exc())


def get_page_hierarchy(root_url, root_path, include_jcr_content=False, **kwargs):
    """Returns a simplified JSON representation of an aem JCR hierarchy for a given url and root path.
    Only includes nodes with jcr:primaryType: "cq:Page"
    NOTE: Does not support authentication
    :param root_url:
        STRING fully qualified url for an aem domain
    :param root_path:
        STRING path to the root node in the JCR
    :param include_jcr_content:
        BOOLEAN a jcr_content key will be included in each path's info containing the 'jcr:content' for the node
    :return:
        JSON dictionary representation of a JCR tree
    """
    # cleanup input strings, add protocol to url if one isn't provided
    root_path = root_path[:-5] if root_path.endswith('.html') else root_path
    root_path = f"/{root_path}" if not root_path.startswith('/') else root_path
    root_url = root_url[:-1] if root_url.endswith('/') else root_url
    if not urlparse(root_url).scheme:
        root_url = "http://" + root_url

    jcr_json = kwargs.get("jcr_json")

    try:
        if not jcr_json or not isinstance(jcr_json, dict):
            jcr_json = get_jcr_content(root_url=root_url, root_path=root_path, infinity=True)

            # Handle depth pagination, get jcr content for highest depth
            if isinstance(jcr_json, list):
                jcr_json = get_jcr_content(
                    root_url=root_url, root_path=jcr_json[0].split('.')[0], depth=jcr_json[0].split('.')[1])

        node_hash = {
            f"{root_path}.html": {
                "url": f"{root_url}{root_path}.html",
                "depth": kwargs.get("depth", 0),
                "template": jcr_json.get("jcr:content").get("cq:template"),
                "children": []
            }
        }

        if include_jcr_content:
            node_hash[f"{root_path}.html"]["jcr_content"] = jcr_json.get("jcr:content")

        # Set node's parent path if it exists, else False
        if "parent_path" in kwargs:
            node_hash[f"{root_path}.html"]["parent"] = f"{(kwargs.get('parent_path'))}.html"
        else:
            node_hash[f"{root_path}.html"]["parent"] = False

        for key, value in jcr_json.iteritems():
            if isinstance(value, dict) and value.get("jcr:primaryType") == "cq:Page":
                node_hash[f"{root_path}.html"]["children"].append(f"{root_path}/{key}.html")
                node_hash.update(get_page_hierarchy(
                    root_url=root_url, root_path=f"{root_path}/{key}", include_jcr_content=include_jcr_content,
                    jcr_json=value, depth=kwargs.get("depth", 0)+1, parent_path=root_path))

        return node_hash
    except AttributeError as ae:
        message = "An error occurred when creating a page hierarchy for the given url and path. " \
                  f"Unexpected or incomplete jcr content received. root_url: {root_url} root_path: {root_path} jcr_json: {jcr_json} | " \
                  f"Exception: {ae.message}"
        raise JCRHelperException(message, stacktrace=traceback.format_exc())


class JCRHelperException(Exception):
    def __init__(self, msg, stacktrace=None, details=None):
        self.msg = msg
        self.details = {} if details is None else details
        self.stacktrace = stacktrace
        super(JCRHelperException, self).__init__()

    def __str__(self):
        exception_msg = "JCR Helper Exception: \n"
        if self.stacktrace is not None:
            exception_msg += f"{self.stacktrace}"
        if self.details:
            detail_string = "\nException Details:\n"
            for key, value in self.details.items():
                detail_string += f"{key}: {value}\n"
            exception_msg += detail_string
        exception_msg += f"Message: {self.msg}"

        return exception_msg
