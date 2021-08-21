# FusionAPI_python
# Author- kantoku
# Description- Convert Sketch Polygon To Circle
# Fusion360API Python addin

import adsk.core
import adsk.fusion
import traceback
import time
from .ktkCmdInputHelper import SelectionCommandInputHelper, TextBoxCommandInputHelper
from .ktkLanguageMessage import LangMsg
from .Polygons2CirclesFactry import Polygons2CirclesFactry as Pol2CirFact

# Multilingual Dictionary
msgDict = {
    'Polygons To Circles': 'ポリゴンから円',
    'Convert Sketch Polygon to Circle': 'ポリゴンスケッチを円に修正します。',
    'Sketch:': 'スケッチ:',
    'Select Sketch or Sketch Entity': 'スケッチ、又はスケッチ要素を選択',
    'Information:': '情報:',
    'Sketch Name': 'スケッチ名',
    'Sketch Lines Count': '直線数',
    'circles were created.': '個の円を作成しました。',
}
lm = LangMsg(msgDict, adsk.core.UserLanguages.JapaneseLanguage)

# command Information
_cmdInfo = {
    'id': 'pol2cir',
    'name': 'Polygons To Circles',
    'tooltip': lm.sLng('Convert Sketch Polygon to Circle'),
    'resources': r'resources\Polygons2Circles'
}

# panel ID
_panelId = 'UtilityPanel'

# sketch select input
_selSkt = SelectionCommandInputHelper(
    'selSkt',
    lm.sLng('Sketch:'),
    lm.sLng('Select Sketch or Sketch Entity'),
    [
        'Sketches',
        'Profiles',
        'Texts',
        'SketchCurves',
        'SketchLines',
        'SketchCircles',
        'SketchPoints',
    ]
)

# Information text input
_info = TextBoxCommandInputHelper(
    'txtInt',
    lm.sLng('Information:'),
    '',
    2,
    True
)

_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_handlers = []


def run(context):
    try:
        global _app, _ui
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # CommandDefinition
        cmdDefs: adsk.core.CommandDefinitions = _ui.commandDefinitions

        global _cmdInfo
        cmdDef: adsk.core.CommandDefinition = cmdDefs.itemById(_cmdInfo['id'])
        if cmdDef:
            cmdDef.deleteMe()

        cmdDef = cmdDefs.addButtonDefinition(
            _cmdInfo['id'],
            _cmdInfo['name'],
            _cmdInfo['tooltip'],
            _cmdInfo['resources']
        )

        # Event
        global _handlers
        onCommandCreated = CommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        # Register Panel
        global _panelId
        targetpanel: adsk.core.ToolbarPanel = _ui.allToolbarPanels.itemById(
            _panelId)
        controls: adsk.core.ToolbarControls = targetpanel.controls
        cmdControl: adsk.core.ToolbarPanel = controls.addCommand(cmdDef)
        cmdControl.isVisible = True

        _app.log(f" -- Start Addin : {_cmdInfo['name']} --")

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def getSketch(entity) -> adsk.fusion.Sketch:
    if entity.objectType == 'adsk::fusion::Sketch':
        return entity

    if hasattr(entity, 'parentSketch'):
        return entity.parentSketch

    return None


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        eventArgs = adsk.core.InputChangedEventArgs.cast(args)

        global _selSkt
        if eventArgs.input.id != _selSkt.id:
            return

        global _info
        txtIpt: adsk.core.TextBoxCommandInput = _info.obj

        if _selSkt.obj.selectionCount < 1:
            txtIpt.text = ''
        skt: adsk.fusion.Sketch = getSketch(_selSkt.obj.selection(0).entity)

        if skt:
            infos = [
                lm.sLng('Sketch Name') + f' : {skt.name}',
                lm.sLng('Sketch Lines Count') +
                f' : {skt.sketchCurves.sketchLines.count}'
            ]
            txtIpt.text = '\n'.join(infos)


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandEventArgs):

        # get sketch
        global _selSkt
        skt: adsk.fusion.Sketch = getSketch(_selSkt.obj.selection(0).entity)
        _selSkt.obj.clearSelection()

        # time
        t = time.time()

        # convert
        p2c = Pol2CirFact(skt)
        count = p2c.execConvert()

        # finish
        msg = f'{count}' + lm.sLng('circles were created.')
        msg += '\n({:.3f} s)'.format(time.time() - t)

        del p2c

        global _app, _ui
        _app.log(msg)
        _ui.messageBox(msg)


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            global _app, _ui, _handlers
            cmd = adsk.core.Command.cast(args.command)
            des: adsk.fusion.Design = _app.activeDocument

            # Event
            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            onInputChanged = InputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)

            # Inputs
            global _selSkt, _info
            inputs: adsk.core.CommandInputs = cmd.commandInputs
            _selSkt.register(inputs)
            _info.register(inputs)

        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        global _app, _ui
        panels: adsk.core.ToolbarPanels = _ui.allToolbarPanels

        global _panelId
        panel: adsk.core.ToolbarPanel = panels.itemById(_panelId)

        global _cmdInfo
        if panel:
            panel.controls.itemById(_cmdInfo['id']).deleteMe()

        cmdDefs: adsk.core.CommandDefinitions = _ui.commandDefinitions
        cmdDef: adsk.core.CommandDefinition = cmdDefs.itemById(_cmdInfo['id'])
        if cmdDef:
            cmdDef.deleteMe()

        _app.log(f" -- Stop Addin : {_cmdInfo['name']} --")

    except:
        print('Failed:\n{}'.format(traceback.format_exc()))
