from bpy.props import BoolProperty, EnumProperty, PointerProperty
from bpy.types import Object
from ..hubs_component import HubsComponent
from ..types import Category, NodeType, PanelType
from ..utils import has_component
from ...io.utils import gather_joint_property, gather_node_property

component_items = []

def get_valid_components(self, context):
    global component_items
    component_items.clear()

    if not self.srcNode:
        return

    if has_component(self.srcNode, 'loop-animation'):
        component_items.append(('loop-animation', "Loop Animation", "Loop Animation"))

    if has_component(self.srcNode, 'video'):
        component_items.append(('video', "Video", "Video"))

    if has_component(self.srcNode, 'audio'):
        component_items.append(('audio', "Audio", "Audio"))

    return component_items

class TriggerVolume(HubsComponent):
    _definition = {
        'name': 'trigger-volume',
        'display_name': 'Trigger Volume (Proximity Trigger)',
        'category': Category.ELEMENTS,
        'node_type': NodeType.NODE,
        'panel_type': [PanelType.OBJECT],
        'icon': 'PLUS'
    }

    srcNode: PointerProperty(
        name="Target",
        description="The object to affect",
        type=Object
    )

    enterComponent: EnumProperty(
        name="Component",
        description="Component to affect when the Trigger Volume is entered",
        items=get_valid_components
    )

    enterProperty: EnumProperty(
        name="Property",
        description="Property to affect when the Trigger Volume is entered",
        items=[("paused", "Paused", "Paused")]
    )

    enterValue: BoolProperty()

    leaveComponent: EnumProperty(
        name="Component",
        description="Component to affect when the Trigger Volume is left",
        items=get_valid_components
    )

    leaveProperty: EnumProperty(
        name="Property",
        description="Property to affect when the Trigger Volume is left",
        items=[("paused", "Paused", "Paused")]
    )

    leaveValue: BoolProperty()

    def gather(self, export_settings, object):
        size = {
            'x': object.scale[0],
            'y': object.scale[1],
            'z': object.scale[2]
        }
        if export_settings['gltf_yup']:
            size['y'] = object.scale[2]
            size['z'] = object.scale[1]

        return {
            "size": size,
            "target": gather_node_property(export_settings, object, self, 'srcNode'),
            "enterComponent": self.enterComponent,
            "enterProperty": self.enterProperty,
            "enterValue": self.enterValue,
            "leaveComponent": self.leaveComponent,
            "leaveProperty": self.leaveProperty,
            "leaveValue": self.leaveValue,
        }

#"name": "Trigger Volume",
      #"extensions": {
        #"MOZ_hubs_components": {
          #"trigger-volume": {
            #"size": {
              #"x": 3,
              #"y": 3,
              #"z": 3
            #},
            #"target": {
              #"__mhc_link_type": "node",
              #"index": 11
            #},
            #"enterComponent": "loop-animation",
            #"enterProperty": "paused",
            #"enterValue": false,
            #"leaveComponent": "loop-animation",
            #"leaveProperty": "paused",
            #"leaveValue": true
          #}
        #}
      #}
    #},
