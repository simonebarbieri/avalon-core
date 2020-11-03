import os
import json
import contextlib

import pyblish.api
from .. import api, io
from . import CommunicationWrapper


METADATA_SECTION = "avalon"
SECTION_NAME_INSTANCES = "instances"
SECTION_NAME_CONTAINERS = "containers"


def install():
    """Install Maya-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(maya)`.

    """
    io.install()

    # Create workdir folder if does not exist yet
    workdir = api.Session["AVALON_WORKDIR"]
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    pyblish.api.register_host("tvpaint")


def uninstall():
    """Uninstall TVPaint-specific functionality of avalon-core.

    This function is called automatically on calling `api.uninstall()`.

    """

    pyblish.api.deregister_host("tvpaint")


def containerise(name, namespace, nodes, context, loader):
    data = {
        "schema": "avalon-core:container-2.0",
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"])
    }
    return json.dumps(data)


@contextlib.contextmanager
def maintained_selection():
    # TODO implement logic
    try:
        yield
    finally:
        pass


def project_metadata(metadata_key):
    """Read metadata for specific key from current project workfile.

    Pipeline use function to store loaded and created instances within keys
    stored in `SECTION_NAME_INSTANCES` and `SECTION_NAME_CONTAINERS`
    constants.

    Args:
        metadata_key (str): Key defying which key should read. It is expected
            value contain json serializable string.
    """
    george_script = (
        "tv_readprojectstring \"{}\" \"{}\" \"[]\""
    ).format(METADATA_SECTION, metadata_key)
    json_string = CommunicationWrapper.execute_george(george_script)
    if json_string:
        data = json.loads(json_string)
    else:
        data = []
    return data


def write_project_metadata(metadata_key, value):
    """Write metadata for specific key into current project workfile.

    George script has specific way how to work with quotes which should be
    solved automatically with this function.

    Args:
        metadata_key (str): Key defying under which key value will be stored.
        value (dict,list,str): Data to store they must be json serializable.
    """
    if isinstance(value, (dict, list)):
        value = json.dumps(value)

    if not value:
        value = ""

    # Handle quotes in dumped json string
    value = (
        value
        # Replace both quotes with placeholder first
        .replace("'", "{single_quote}").replace("\"", "{quote}")
        # Replace plaholders with right values for george script
        .replace("{single_quote}", "'\"'").replace("{quote}", "\"'\"")
    )

    george_script = (
        "tv_writeprojectstring \"{}\" \"{}\" \"{}\""
    ).format(METADATA_SECTION, metadata_key, value)
    return CommunicationWrapper.execute_george_through_file(george_script)


def list_instances():
    return project_metadata(SECTION_NAME_INSTANCES)


def ls():
    return project_metadata(SECTION_NAME_CONTAINERS)


class TVPaintCreator(api.Creator):
    def process(self):
        data = list_instances()
        data.append(self.data)
        write_project_metadata(SECTION_NAME_INSTANCES, data)


class TVPaintLoader(api.Loader):
    hosts = ["tvpaint"]
