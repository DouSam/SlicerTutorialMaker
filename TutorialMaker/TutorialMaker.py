import logging
import os
import qt
import vtk
import slicer
import logging
import importlib
import Lib.utils as utils
import Lib.painter as AnnotationPainter

from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.i18n import tr as _
from slicer.i18n import translate
from Lib.TutorialEditor import TutorialEditor
from Lib.TutorialGUI import TutorialGUI

#
# TutorialMaker
#

class TutorialMaker(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Tutorial Maker")  # TODO: make this more human readable by adding spaces
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Utilities")]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Douglas Gonçalves (USP)", "Enrique Hernández (UAEM)", "João Januário (USP)", "Lucas Silva (USP)", "Victor Montaño (UAEM)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """help text"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
        Development of this module was funded by <a href="https://chanzuckerberg.com/eoss/proposals/3d-slicer-for-latin-america-localization-and-outreach/">CZI EOSS grant</a>.
        """)

#
# TutorialMakerWidget
#

class TutorialMakerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False
        self.__tableSize = 0
        self.__selectedTutorial = None
        self.isDebug = True

        #PROTOTYPE FOR PLAYBACK

        self.actionList = []
        
    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/TutorialMaker.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = TutorialMakerLogic()

        # will only draw the circle at playback for now
        #self.widgetFinder.sinalManager.connect(self.widgetPainter.setTargetWidget)

        # Buttons

        #Dynamic Tutorial Prototype
        self.ui.pushButtonEdit.connect('clicked(bool)', self.logic.Edit)
        self.ui.pushButtonSave.connect('clicked(bool)', self.logic.Save)
        self.ui.pushButtonLoad.connect('clicked(bool)', self.logic.Load)
        self.ui.pushButtonExportScreenshots.connect('clicked(bool)', self.logic.ExportScreenshots)
        self.ui.listWidgetTutorials.itemSelectionChanged.connect(self.tutorialSelectionChanged)

        #Static Tutorial Handlers
        self.ui.pushButtonAnnotate.connect('clicked(bool)', self.annotateButton)
        if not self.isDebug:
            self.ui.CollapsibleButtonTutorialMaking.setVisible(0)
            self.ui.pushButtonTestPainter.connect('clicked(bool)', self.testPainterButton)
            self.ui.pushButtonTestPainter.setVisible(0)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        #Update GUI
        self.populateTutorialList()

        #Verify if the folders to manipulate the tutorials are created
        utils.util.verifyOutputFolders(self)

    def cleanup(self):
        self.logic.exitTutorialEditor()
        """
        Called when the application closes and the module widget is destroyed.
        """
        return

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        #self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        print('goodbye, world!')
    
    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        return

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        return
        
    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """
        return
    
    def testPainterButton(self):
        self.logic.TestPainter(self.__selectedTutorial)

    def annotateButton(self):
        self.logic.Annotate(self.__selectedTutorial)
    
    def tutorialSelectionChanged(self):
        self.__selectedTutorial = self.ui.listWidgetTutorials.selectedItems()[0].data(0)
        self.ui.pushButtonAnnotate.setEnabled(not (self.__selectedTutorial is None))
        if self.isDebug:
            self.ui.pushButtonTestPainter.setEnabled(not (self.__selectedTutorial is None))

    
    def populateTutorialList(self):
        loadedTutorials = self.logic.loadTutorials()
        listWidget = self.ui.listWidgetTutorials
        listWidget.addItems(loadedTutorials)

#
# TutorialMakerLogic
#
class TutorialMakerLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
        self.tutorialEditor = TutorialEditor()


    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        print("World!")
        
    def exitTutorialEditor(self):
        self.tutorialEditor.exit()

    def Edit(self):
        self.tutorialEditor.Show()
        pass

    def Save(self):
        pass

    def Load(self):
        pass

    def ExportScreenshots(self):
        screenshot = utils.ScreenshotTools()
        screenshot.saveScreenshotMetadata(0)
        pass

    def Annotate(self, tutorialName):
        TutorialMakerTest().test_TutorialMaker1(tutorialName)
        
        Annotator = TutorialGUI()
        Annotator.open_json_file(os.path.dirname(slicer.util.modulePath("TutorialMaker")) + "/Outputs/Raw/Tutorial.json")
        Annotator.set_output_name(tutorialName)
        Annotator.show()
        pass

    def TestPainter(self, tutorialName):
        AnnotationPainter.ImageDrawer.StartPaint(os.path.dirname(slicer.util.modulePath("TutorialMaker")) + "/Outputs/Annotations/"+tutorialName+".json")
        pass

    def loadTutorials(self):
        test_tutorials = []
        test_contents = os.listdir(os.path.dirname(slicer.util.modulePath("TutorialMaker")) + "/Testing/")
        for content in test_contents:
            if(not (".py" in content)):
                continue
            test_tutorials.append(content.replace(".py", ""))
        return test_tutorials

#
# TutorialMakerTest
#
class TutorialMakerTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        #Annotator test
        #Screencapture test
        #Then run all the tutorials
        tutorials_failed = 0
        test_tutorials = os.listdir(os.path.dirname(slicer.util.modulePath("TutorialMaker")) + "/Testing/")
        for unit_tutorials in test_tutorials:
            try:
                if(not (".py" in unit_tutorials)):
                    continue
                unit_tutorials = unit_tutorials.replace(".py", "")
                # Generate Screenshots and widget metadata
                self.test_TutorialMaker1(unit_tutorials)
                # Paint Screenshots with annotations
                AnnotationPainter.ImageDrawer.StartPaint(os.path.dirname(slicer.util.modulePath("TutorialMaker")) + "/Outputs/Annotations/" + unit_tutorials + ".json")
            except:
                logging.error(_("Tutorial Execution Failed: {unit_tutorials}".format(unit_tutorials=unit_tutorials)))
                tutorials_failed = tutorials_failed + 1
                pass
            finally:
                self.delayDisplay(_("Tutorial Tested"))
            pass
        if tutorials_failed > 0:
            raise Exception(_("{tutorials_failed} tutorials failed to execute".format(tutorials_failed=tutorials_failed)))


    def test_TutorialMaker1(self, tutorial_name):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """
        TutorialModule = importlib.import_module("Testing." + tutorial_name)
        for className in TutorialModule.__dict__:
            if(not ("Test" in className) or className == "ScriptedLoadableModuleTest"):
                continue
            testClass = getattr(TutorialModule, className)
            tutorial = testClass()
            tutorial.runTest()
            return
        logging.error(_("No tests found in {tutorial_name}".format(tutorial_name=tutorial_name)))
        raise Exception(_("No Tests Found"))
        pass

    def test_TutorialMaker2(self):
        pass

    def delayDisplay(self, message, requestedDelay=None, msec=None):
        """
        Display messages to the user/tester during testing.

        By default, the delay is 50ms.

        The function accepts the keyword arguments ``requestedDelay`` or ``msec``. If both
        are specified, the value associated with ``msec`` is used.

        This method can be temporarily overridden to allow tests running
        with longer or shorter message display time.

        Displaying a dialog and waiting does two things:
        1) it lets the event loop catch up to the state of the test so
        that rendering and widget updates have all taken place before
        the test continues and
        2) it shows the user/developer/tester the state of the test
        so that we'll know when it breaks.

        Note:
        Information that might be useful (but not important enough to show
        to the user) can be logged using logging.info() function
        (printed to console and application log) or logging.debug()
        function (printed to application log only).
        Error messages should be logged by logging.error() function
        and displayed to user by slicer.util.errorDisplay function.
        """
        if hasattr(self, "messageDelay"):
            msec = self.messageDelay
        if msec is None:
            msec = requestedDelay
        if msec is None:
            msec = 100

        slicer.util.delayDisplay(message, msec)






        
