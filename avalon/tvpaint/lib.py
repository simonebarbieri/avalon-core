import os
import tempfile

from . import CommunicationWrapper


def execute_george(george_script):
    return CommunicationWrapper.execute_george(george_script)


def execute_george_through_file(george_script):
    """Execute george script with temp file.

    Allows to execute multiline george script without stopping websocket
    client.

    On windows make sure script does not contain paths with backwards
    slashes in paths, TVPaint won't execute properly in that case.

    Args:
        george_script (str): George script to execute. May be multilined.
    """
    temporary_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".grg", delete=False
    )
    temporary_file.write(george_script)
    temporary_file.close()
    temp_file_path = temporary_file.name.replace("\\", "/")
    execute_george("tv_runscript {}".format(temp_file_path))
    os.remove(temp_file_path)


def parse_layers_data(data):
    layers = []
    layers_raw = data.split("\n")
    for layer_raw in layers_raw:
        layer_raw = layer_raw.strip()
        if not layer_raw:
            continue
        (
            layer_id, group_id, visible, position, opacity, name,
            layer_type,
            frame_start, frame_end, prelighttable, postlighttable,
            selected, editable, sencil_state
        ) = layer_raw.split("|")
        layer = {
            "id": int(layer_id),
            "group_id": int(group_id),
            "visible": visible == "ON",
            "position": int(position),
            "opacity": int(opacity),
            "name": name,
            "type": layer_type,
            "frame_start": int(frame_start),
            "frame_end": int(frame_end),
            "prelighttable": prelighttable == "1",
            "postlighttable": postlighttable == "1",
            "selected": selected == "1",
            "editable": editable == "1",
            "sencil_state": sencil_state
        }
        layers.append(layer)
    return layers


def layers_data():
    output_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    )
    output_file.close()

    output_filepath = output_file.name.replace("\\", "/")
    george_script_lines = (
        # Variable containing full path to output file
        "output_path = \"{}\"".format(output_filepath),
        # Get Current Layer ID
        "tv_LayerCurrentID",
        "current_layer_id = result",
        # Layer loop variables
        "loop = 1",
        "idx = 0",
        # Layers loop
        "WHILE loop",
        "tv_LayerGetID idx",
        "layer_id = result",
        "idx = idx + 1",
        # Stop loop if layer_id is "NONE"
        "IF CMP(layer_id, \"NONE\")==1",
        "loop = 0",
        "ELSE",
        # Get information about layer's group
        "tv_layercolor \"get\" layer_id",
        "group_id = result",
        "tv_LayerInfo layer_id",
        (
            "PARSE result visible position opacity name"
            " type startFrame endFrame prelighttable postlighttable"
            " selected editable sencilState"
        ),
        # Check if layer ID match `tv_LayerCurrentID`
        "IF CMP(current_layer_id, layer_id)==1",
        # - mark layer as selected if layer id match to current layer id
        "selected=1",
        "END",
        # Prepare line with data separated by "|"
        (
            "line = layer_id'|'group_id'|'visible'|'position'|'opacity'|'"
            "name'|'type'|'startFrame'|'endFrame'|'prelighttable'|'"
            "postlighttable'|'selected'|'editable'|'sencilState"
        ),
        # Write data to output file
        "tv_writetextfile \"strict\" \"append\" '\"'output_path'\"' line",
        "END",
        "END"
    )
    george_script = "\n".join(george_script_lines)
    execute_george_through_file(george_script)

    with open(output_filepath, "r") as stream:
        data = stream.read()

    output = parse_layers_data(data)
    os.remove(output_filepath)
    return output
