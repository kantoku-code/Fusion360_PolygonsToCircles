# FusionAPI_python
# Author- kantoku
# Description- Convert Sketch Polygon To Circle
# Fusion360API Python addin

from .ktkLanguageMessage import LangMsg
import traceback
import adsk.fusion
import adsk.core
import math
import os
import sys
import pathlib

this_dir = pathlib.Path(__file__).resolve().parent
my_dir = this_dir.parents[2]

osModules = 'Win'
if os.name == "posix":
    osModules = 'Mac'

app = adsk.core.Application.get()
app.log(str(this_dir))
app.log(str(my_dir))

sys.path.append(str(my_dir / 'Modules' / osModules))
sys.path.append(str(this_dir / 'Modules' / osModules))

try:
    import numpy as np
except:
    app.log('numpy not found')
finally:
    del sys.path[-1]
    del sys.path[-1]

# Multilingual Dictionary
msgDict = {
    'Convert Polygons': 'ポリゴンを変換中',
    'Find Polygons': 'ポリゴン検索中',
    'Polygons To Circles': 'ポリゴンから円',
    'in preparation ....': '準備中 ....',
    'Processing....': '処理中....',
}
lm = LangMsg(msgDict, adsk.core.UserLanguages.JapaneseLanguage)


class Polygons2CirclesFactry():
    def __init__(self, skt: adsk.fusion.Sketch):
        super().__init__()

        self.skt: adsk.fusion.Sketch = skt
        self.areConstraintsShown: bool = skt.areConstraintsShown
        self.areDimensionsShown: bool = skt.areDimensionsShown
        self.arePointsShown: bool = skt.arePointsShown
        self.areProfilesShown: bool = skt.areProfilesShown

        self.sktCurvesGroup: list = []
        self.fitCircles: list = []

        self.progress: adsk.core.ProgressDialog = None
        self.cancel: bool = False

    def execConvert(self) -> int:

        # ProgressDialog
        self._initProgress(self.skt.profiles.count)

        # Stop Sketch Property
        self._stopSketchProperty()

        # Get convertible polygons & fittingCircles
        self._getConvertPolygons()
        if len(self.sktCurvesGroup) < 1:
            self._reviveSketchProperty()
            return 0

        if self.cancel:
            self._reviveSketchProperty()
            return 0

        # ProgressDialog reset
        self._resetProgress(len(self.fitCircles))

        # Create Circle
        self._ply2Circles()

        self._reviveSketchProperty()
        return len(self.fitCircles)

    # -- Support Functions --
    def _ply2Circles(
            self):

        self.skt.isComputeDeferred = True

        circles: adsk.fusion.SketchCircles = self.skt.sketchCurves.sketchCircles
        for idx, c in enumerate(self.fitCircles):

            if self._updeteProgress(lm.sLng('Convert Polygons')):
                self.cancel = True
                return

            for line in self.sktCurvesGroup[idx]:
                line.isConstruction = True

            circles.addByCenterRadius(c.center, c.radius)

        self.skt.isComputeDeferred = False

    def _getConvertPolygons(
            self):

        proCurvesGroup = [
            pro.profileLoops[0].profileCurves for pro in self.skt.profiles]

        sktCurvesGroup = []
        fitCircles = []
        for proCurves in proCurvesGroup:
            if self._updeteProgress(lm.sLng('Find Polygons')):
                sktCurvesGroup = []
                fitCircles = []
                self.cancel = True
                break

            # sketch curves
            sktCurves = [c.sketchEntity for c in proCurves]

            # count check
            if len(sktCurves) < 3:
                continue

            # line only
            if not self._isLineOnly(sktCurves):
                continue

            # fitting Circles
            fitCircle: adsk.core.Circle3D = self._getFittingCircle(sktCurves)

            # can convert?
            if not self._canConvert(sktCurves, fitCircle):
                continue

            sktCurvesGroup.append(sktCurves)
            fitCircles.append(fitCircle)

            self.sktCurvesGroup = sktCurvesGroup
            self.fitCircles = fitCircles

    def _canConvert(
            self,
            lines: list,
            refCircle: adsk.core.Circle3D,
            tolerance: float = 0.01) -> bool:

        startPoints = [l.startSketchPoint.geometry for l in lines]

        gaps = [abs(s.distanceTo(refCircle.center) - refCircle.radius)
                for s in startPoints]
        for gap in gaps:
            if gap > tolerance:
                return False

        endPoints = [l.endSketchPoint.geometry for l in lines]
        lengths = [l.length for l in lines]
        chords = [self._getTheoreticalChord(refCircle, s, e, tolerance)
                  for s, e in zip(startPoints, endPoints)]

        for le, ch in zip(lengths, chords):
            if abs(le - ch) > tolerance:
                return False

        return True

    def _getTheoreticalChord(
            self,
            circle: adsk.core.Circle3D,
            p1: adsk.core.Point3D,
            p2: adsk.core.Point3D,
            tolerance: float) -> float:

        app: adsk.core.Application = adsk.core.Application.get()
        measMgr: adsk.core.MeasureManager = app.measureManager

        l1: adsk.core.Line3D = adsk.core.Line3D.create(circle.center, p1)
        l2: adsk.core.Line3D = adsk.core.Line3D.create(circle.center, p2)

        angle = measMgr.measureAngle(l1, l2).value

        return math.tan(angle * 0.5) * (circle.radius - tolerance) * 2

    def _getFittingCircle(
            self,
            lines: list) -> adsk.core.Circle3D:
        # https://mori-memo.hateblo.jp/entry/2020/04/27/205437

        points = [l.startSketchPoint.geometry for l in lines]

        x = np.array([p.x for p in points])
        y = np.array([p.y for p in points])

        A = np.vstack((x, y, np.ones((len(x))))).T
        v = -(x ** 2 + y ** 2)
        u, residuals, rank, s = np.linalg.lstsq(A, v, rcond=None)

        cx_pred = u[0] / (-2)
        cy_pred = u[1] / (-2)
        r_pred = np.sqrt(cx_pred ** 2 + cy_pred ** 2 - u[2])

        return adsk.core.Circle3D.createByCenter(
            adsk.core.Point3D.create(cx_pred, cy_pred, 0),
            adsk.core.Vector3D.create(0, 0, 1),
            r_pred
        )

    def _isLineOnly(
            self,
            curves: list) -> bool:

        sktLine = 'adsk::fusion::SketchLine'
        return all([c.objectType == sktLine for c in curves]) if curves else False

    def _stopSketchProperty(self):
        self.skt.areConstraintsShown = False
        self.skt.areDimensionsShown = False
        self.skt.arePointsShown = False
        self.skt.areProfilesShown = False

    def _reviveSketchProperty(self):
        self.skt.areConstraintsShown = self.areConstraintsShown
        self.skt.areDimensionsShown = self.areDimensionsShown
        self.skt.arePointsShown = self.arePointsShown
        self.skt.areProfilesShown = self.areProfilesShown

    # progress dialog

    def _initProgress(
            self,
            maxCount: int) -> adsk.core.ProgressDialog:

        app: adsk.fusion.Application = adsk.core.Application.get()
        self.progress = app.userInterface.createProgressDialog()
        self.progress.isCancelButtonShown = True
        self.progress.show(
            lm.sLng('Polygons To Circles'),
            lm.sLng('in preparation ....'),
            1,
            maxCount
        )

    def _updeteProgress(
            self,
            msg: str) -> bool:

        self.progress.progressValue += 1
        stateValue = f'{self.progress.progressValue}/{self.progress.maximumValue}'
        self.progress.message = lm.sLng(
            'Processing....') + f' {msg} {stateValue}'
        adsk.doEvents()
        return self.progress.wasCancelled

    def _resetProgress(
            self,
            maxCount: int):

        self.progress.reset()
        self.progress.minimumValue = 1
        self.progress.maximumValue = maxCount
