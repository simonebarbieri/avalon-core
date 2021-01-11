import os
import re
import json
import contextlib
import uuid
import tempfile

import pyblish.api
from .. import api, io
from . import lib
from ..pipeline import AVALON_CONTAINER_ID


METADATA_SECTION = "avalon"
SECTION_NAME_CONTEXT = "context"
SECTION_NAME_INSTANCES = "instances"
SECTION_NAME_CONTAINERS = "containers"
# Maximum length of metadata chunk string
# TODO find out the max (500 is safe enough)
TVPAINT_CHUNK_LENGTH = 500

"""TVPaint's Metadata

Metadata are stored to TVPaint's workfile.

Workfile works similar to .ini file but has few limitation. Most important
limitation is that value under key has limited length. Due to this limitation
each metadata section/key stores number of "subkeys" that are related to
the section.

Example:
Metadata key `"instances"` may have stored value "2". In that case it is
expected that there are also keys `["instances0", "instances1"]`.

Workfile data looks like:
```
[avalon]
instances0=[{{__dq__}id{__dq__}: {__dq__}pyblish.avalon.instance{__dq__...
instances1=...more data...
instances=2
```
"""


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


def containerise(
    name, namespace, layer_ids, context, loader, current_containers=None
):
    """Add new container to metadata.

    Args:
        name (str): Container name.
        namespace (str): Container namespace.
        layer_ids (list): List of layer that were loaded and belongs to the
            container.
        current_containers (list): Preloaded containers. Should be used only
            on update/switch when containers were modified durring the process.

    Returns:
        dict: Container data stored to workfile metadata.
    """

    container_data = {
        "schema": "avalon-core:container-2.0",
        "id": AVALON_CONTAINER_ID,
        "members": layer_ids,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": str(context["representation"]["_id"])
    }
    if current_containers is None:
        current_containers = ls()

    # Add container to containers list
    current_containers.append(container_data)

    # Store data to metadata
    write_workfile_metadata(SECTION_NAME_CONTAINERS, current_containers)

    return container_data


@contextlib.contextmanager
def maintained_selection():
    # TODO implement logic
    try:
        yield
    finally:
        pass


def split_metadata_string(text, chunk_length=None):
    """Split string by length.

    Split text to chunks by entered length.
    Example:
        ```python
        text = "ABCDEFGHIJKLM"
        result = split_metadata_string(text, 3)
        print(result)
        >>> ['ABC', 'DEF', 'GHI', 'JKL']
        ```

    Args:
        text (str): Text that will be split into chunks.
        chunk_length (int): Single chunk size. Default chunk_length is
            set to global variable `TVPAINT_CHUNK_LENGTH`.

    Returns:
        list: List of strings wil at least one item.
    """
    if chunk_length is None:
        chunk_length = TVPAINT_CHUNK_LENGTH
    chunks = []
    for idx in range(chunk_length, len(text) + chunk_length, chunk_length):
        start_idx = idx - chunk_length
        chunks.append(text[start_idx:idx])
    return chunks


def get_workfile_metadata_string_for_keys(metadata_keys):
    """Read metadata for specific keys from current project workfile.

    All values from entered keys are stored to single string without separator.

    Function is designed to help get all values for one metadata key at once.
    So order of passed keys matteres.

    Args:
        metadata_keys (list, str): Metadata keys for which data should be
            retrieved. Order of keys matters! It is possible to enter only
            single key as string.
    """
    # Add ability to pass only single key
    if isinstance(metadata_keys, str):
        metadata_keys = [metadata_keys]

    output_file = tempfile.NamedTemporaryFile(
        mode="w", prefix="a_tvp_", suffix=".txt", delete=False
    )
    output_file.close()
    output_filepath = output_file.name.replace("\\", "/")

    george_script_parts = []
    george_script_parts.append(
        "output_path = \"{}\"".format(output_filepath)
    )
    # Store data for each index of metadata key
    for metadata_key in metadata_keys:
        george_script_parts.append(
            "tv_readprojectstring \"{}\" \"{}\" \"\"".format(
                METADATA_SECTION, metadata_key
            )
        )
        george_script_parts.append(
            "tv_writetextfile \"strict\" \"append\" '\"'output_path'\"' result"
        )

    # Execute the script
    george_script = "\n".join(george_script_parts)
    lib.execute_george_through_file(george_script)

    # Load data from temp file
    with open(output_filepath, "r") as stream:
        file_content = stream.read()

    # Remove `\n` from content
    output_string = file_content.replace("\n", "")

    # Delete temp file
    os.remove(output_filepath)

    return output_string


def get_workfile_metadata_string(metadata_key):
    """Read metadata for specific key from current project workfile."""
    result = get_workfile_metadata_string_for_keys([metadata_key])
    if not result:
        return None

    stripped_result = result.strip()
    if not stripped_result:
        return None

    # NOTE Backwards compatibility when metadata key did not store range of key
    #   indexes but the value itself
    # NOTE We don't have to care about negative values with `isdecimal` check
    if not stripped_result.isdecimal():
        json_string = result
    else:
        keys = []
        for idx in range(int(stripped_result)):
            keys.append("{}{}".format(metadata_key, idx))
        json_string = get_workfile_metadata_string_for_keys(keys)

    # Replace quotes plaholders with their values
    json_string = (
        json_string
        .replace("{__sq__}", "'")
        .replace("{__dq__}", "\"")
    )
    return json_string


def get_workfile_metadata(metadata_key, default=None):
    """Read and parse metadata for specific key from current project workfile.

    Pipeline use function to store loaded and created instances within keys
    stored in `SECTION_NAME_INSTANCES` and `SECTION_NAME_CONTAINERS`
    constants.

    Args:
        metadata_key (str): Key defying which key should read. It is expected
            value contain json serializable string.
    """
    if default is None:
        default = []

    json_string = get_workfile_metadata_string(metadata_key)
    if json_string:
        return json.loads(json_string)
    return default


def write_workfile_metadata(metadata_key, value):
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
    # - replace single and double quotes with placeholders
    value = (
        value
        .replace("'", "{__sq__}")
        .replace("\"", "{__dq__}")
    )
    chunks = split_metadata_string(value)
    chunks_len = len(chunks)

    write_template = "tv_writeprojectstring \"{}\" \"{}\" \"{}\""
    george_script_parts = []
    # Add information about chunks length to metadata key itself
    george_script_parts.append(
        write_template.format(METADATA_SECTION, metadata_key, chunks_len)
    )
    # Add chunk values to indexed metadata keys
    for idx, chunk_value in enumerate(chunks):
        sub_key = "{}{}".format(metadata_key, idx)
        george_script_parts.append(
            write_template.format(METADATA_SECTION, sub_key, chunk_value)
        )

    george_script = "\n".join(george_script_parts)

    return lib.execute_george_through_file(george_script)


def get_current_workfile_context():
    """Return context in which was workfile saved."""
    return get_workfile_metadata(SECTION_NAME_CONTEXT, {})


def save_current_workfile_context(context):
    """Save context which was used to create a workfile."""
    return write_workfile_metadata(SECTION_NAME_CONTEXT, context)


def remove_instance(instance):
    """Remove instance from current workfile metadata."""
    current_instances = get_workfile_metadata(SECTION_NAME_INSTANCES)
    instance_id = instance.get("uuid")
    found_idx = None
    if instance_id:
        for idx, _inst in enumerate(current_instances):
            if _inst["uuid"] == instance_id:
                found_idx = idx
                break

    if found_idx is None:
        return
    current_instances.pop(found_idx)
    _write_instances(current_instances)


def list_instances():
    """List all created instances from current workfile."""
    return get_workfile_metadata(SECTION_NAME_INSTANCES)


def _write_instances(data):
    return write_workfile_metadata(SECTION_NAME_INSTANCES, data)


def ls():
    return get_workfile_metadata(SECTION_NAME_CONTAINERS)


class Creator(api.Creator):
    def __init__(self, *args, **kwargs):
        super(Creator, self).__init__(*args, **kwargs)
        # Add unified identifier created with `uuid` module
        self.data["uuid"] = str(uuid.uuid4())

    @staticmethod
    def are_instances_same(instance_1, instance_2):
        """Compare instances but skip keys with unique values.

        During compare are skiped keys that will be 100% sure
        different on new instance, like "id".

        Returns:
            bool: True if instances are same.
        """
        if (
            not isinstance(instance_1, dict)
            or not isinstance(instance_2, dict)
        ):
            return instance_1 == instance_2

        checked_keys = set()
        checked_keys.add("id")
        for key, value in instance_1.items():
            if key not in checked_keys:
                if key not in instance_2:
                    return False
                if value != instance_2[key]:
                    return False
                checked_keys.add(key)

        for key in instance_2.keys():
            if key not in checked_keys:
                return False
        return True

    def write_instances(self, data):
        self.log.debug(
            "Storing instance data to workfile. {}".format(str(data))
        )
        return _write_instances(data)

    def process(self):
        data = list_instances()
        data.append(self.data)
        self.write_instances(data)


class Loader(api.Loader):
    hosts = ["tvpaint"]

    @staticmethod
    def layer_ids_from_container(container):
        if "members" not in container and "objectName" in container:
            # Backwards compatibility
            layer_ids_str = container.get("objectName")
            return [
                int(layer_id) for layer_id in layer_ids_str.split("|")
            ]
        return container["members"]

    def get_unique_layer_name(self, asset_name, name):
        """Layer name with counter as suffix.

        Find higher 3 digit suffix from all layer names in scene matching regex
        `{asset_name}_{name}_{suffix}`. Higher 3 digit suffix is used
        as base for next number if scene does not contain layer matching regex
        `0` is used ase base.

        Args:
            asset_name (str): Name of subset's parent asset document.
            name (str): Name of loaded subset.

        Returns:
            (str): `{asset_name}_{name}_{higher suffix + 1}`
        """
        layer_name_base = "{}_{}".format(asset_name, name)

        counter_regex = re.compile(r"_(\d{3})$")

        higher_counter = 0
        for layer in lib.layers_data():
            layer_name = layer["name"]
            if not layer_name.startswith(layer_name_base):
                continue
            number_subpart = layer_name[len(layer_name_base):]
            groups = counter_regex.findall(number_subpart)
            if len(groups) != 1:
                continue

            counter = int(groups[0])
            if counter > higher_counter:
                higher_counter = counter
                continue

        return "{}_{:0>3d}".format(layer_name_base, higher_counter + 1)
