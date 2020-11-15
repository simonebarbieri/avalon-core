import os
import importlib
import logging
from bson.objectid import ObjectId
from ... import api, style
from ...vendor import qtawesome, six
from ...pipeline import (
    is_compatible_loader,
    _make_backwards_compatible_loader,
    IncompatibleLoaderError
)
from pypeapp import Roots


log = logging.getLogger(__name__)


# `find_config` from `pipeline`
def find_config():
    log.info("Finding configuration for project..")

    config = os.environ["AVALON_CONFIG"]

    if not config:
        raise EnvironmentError(
            "No configuration found in "
            "the project nor environment"
        )

    log.info("Found %s, loading.." % config)
    return importlib.import_module(config)


# loaders_from_representation
#     - added 'dbcon' to args
def loaders_from_representation(dbcon, loaders, representation):
    """Return all compatible loaders for a representation."""
    context = get_representation_context(dbcon, representation)
    return [l for l in loaders if is_compatible_loader(l, context)]


# get_representation_context
#     - added 'dbcon' to args replaced 'io' in code
def get_representation_context(dbcon, representation):
    """Return parenthood context for representation.

    Args:
        representation (str or io.ObjectId or dict): The representation id
            or full representation as returned by the database.

    Returns:
        dict: The full representation context.

    """

    assert representation is not None, "This is a bug"

    if isinstance(representation, (six.string_types, ObjectId)):
        representation = dbcon.find_one(
            {"_id": ObjectId(str(representation))})

    version, subset, asset, project = dbcon.parenthood(representation)

    assert all([representation, version, subset, asset, project]), (
        "This is a bug"
    )

    context = {
        "project": project,
        "asset": asset,
        "subset": subset,
        "version": version,
        "representation": representation,
    }

    return context


# load
def load(
    dbcon, Loader, representation, namespace=None, name=None, options=None,
    **kwargs
):
    """Use Loader to load a representation.

    Args:
        Loader (Loader): The loader class to trigger.
        representation (str or io.ObjectId or dict): The representation id
            or full representation as returned by the database.
        namespace (str, Optional): The namespace to assign. Defaults to None.
        name (str, Optional): The name to assign. Defaults to subset name.
        options (dict, Optional): Additional options to pass on to the loader.

    Returns:
        The return of the `loader.load()` method.

    Raises:
        IncompatibleLoaderError: When the loader is not compatible with
            the representation.

    """

    Loader = _make_backwards_compatible_loader(Loader)
    context = get_representation_context(dbcon, representation)

    # Ensure the Loader is compatible for the representation
    if not is_compatible_loader(Loader, context):
        raise IncompatibleLoaderError("Loader {} is incompatible with "
                                      "{}".format(Loader.__name__,
                                                  context["subset"]["name"]))

    # Ensure options is a dictionary when no explicit options provided
    if options is None:
        options = kwargs.get("data", dict())  # "data" for backward compat

    assert isinstance(options, dict), "Options must be a dictionary"

    # Fallback to subset when name is None
    if name is None:
        name = context["subset"]["name"]

    log.info(
        "Running '%s' on '%s'" % (Loader.__name__, context["asset"]["name"])
    )

    loader = Loader(context)
    return loader.load(context, name, namespace, options)


class RegisteredRoots:
    roots_per_project = {}

    @classmethod
    def registered_root(cls, dbcon):
        project_name = dbcon.Session.get("AVALON_PROJECT")
        if project_name not in cls.roots_per_project:
            cls.roots_per_project[project_name] = Roots(project_name).roots

        return cls.roots_per_project[project_name]
