from .. import api, pipeline
from . import lib
from ..vendor import Qt
from collections import namedtuple

import pyblish.api


def install():
    """Install Photoshop-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(photoshop)`.
    """
    print("Installing Avalon AfterEffects...")
    pyblish.api.register_host("aftereffects")


def ls():
    """Yields containers from active AfterEffects document

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Photoshop; once loaded
    they are called 'containers'

    Yields:
        dict: container

    """
    try:
        stub = lib.stub()  # only after AfterEffects is up
    except lib.ConnectionNotEstablishedYet:
        print("Not connected yet, ignoring")
        return

    return []  # TODO


class Creator(api.Creator):
    """Creator plugin to create instances in AfterEffects

    A LayerSet is created to support any number of layers in an instance. If
    the selection is used, these layers will be added to the LayerSet.
    """

    def process(self):
        # Photoshop can have multiple LayerSets with the same name, which does
        # not work with Avalon.
        msg = "Instance with name \"{}\" already exists.".format(self.name)
        stub = lib.stub()  # only after Photoshop is up

def containerise(name,
                 namespace,
                 layer,
                 context,
                 loader=None,
                 suffix="_CON"):
    """Imprint layer with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        layer (Layer): Layer to containerise
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Name of container assembly
    """
    pass
