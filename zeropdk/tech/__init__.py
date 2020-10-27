import klayout.db as kdb


class Tech:
    layers = None

    def __init__(self):
        if self.layers is None:
            self.layers = dict()

    def add_layer(self, layer_name, layer_def):
        """Adds a layer to the technology file.
        layer_name: str: name of layer. (Useless in GDS, useful in OASIS)
        layer_def: str: 10/0, 10 = layer index, 0, datatype
        """

        layer_idx, datatype = layer_def.split("/")
        layer_idx = int(layer_idx)
        datatype = int(datatype)
        self.layers[layer_name] = kdb.LayerInfo(layer_idx, datatype, layer_name)

    @classmethod
    def load_from_xml(cls, lyp_filename):
        import os

        lyp_filepath = os.path.realpath(lyp_filename)
        with open(lyp_filepath, "r") as file:
            layer_dict = xml_to_dict(file.read())["layer-properties"]["properties"]

        layer_map = {}

        for k in layer_dict:
            layerInfo = k["source"].split("@")[0]
            if "group-members" in k:
                # encoutered a layer group, look inside:
                j = k["group-members"]
                if "name" in j:
                    layerInfo_j = j["source"].split("@")[0]
                    layer_map[j["name"]] = layerInfo_j
                else:
                    for j in k["group-members"]:
                        layerInfo_j = j["source"].split("@")[0]
                        layer_map[j["name"]] = layerInfo_j
                if k["source"] != "*/*@*":
                    layer_map[k["name"]] = layerInfo
            else:
                try:
                    layer_map[k["name"]] = layerInfo
                except TypeError as e:
                    new_message = (
                        "Bad name for layer {}. Check your .lyp XML file for errors.".format(
                            layerInfo
                        )
                    )
                    raise TypeError(new_message) from e

        # layer_map should contain values like '12/0'
        # 12 is the layer and 0 is the datatype

        obj = cls()

        for layer_name, layer_string in layer_map.items():
            obj.add_layer(layer_name, layer_string)

        return obj


# XML functions


def etree_to_dict(t):
    """XML to Dict parser
    from: https://stackoverflow.com/questions/2148119/how-to-convert-an-xml-string-to-a-dictionary-in-python/10077069
    """
    from collections import defaultdict

    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    return d


def xml_to_dict(t):
    from xml.etree import ElementTree as ET

    try:
        e = ET.XML(t)
    except ET.ParseError:
        raise
    except Exception:
        raise UserWarning("Error in the XML file.")
    return etree_to_dict(e)
