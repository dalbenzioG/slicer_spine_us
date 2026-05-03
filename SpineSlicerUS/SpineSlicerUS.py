import logging
import numpy as np
import os
import json
from datetime import datetime, timezone
from typing import Annotated, Optional
import qt
import vtk
import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import (
    vtkMRMLScalarVolumeNode, 
    vtkMRMLLabelMapVolumeNode,
    vtkMRMLVolumeReconstructionNode, 
    vtkMRMLLinearTransformNode, 
    vtkMRMLIGTLConnectorNode,
    vtkMRMLSequenceBrowserNode
)


#
# SpineSlicerUS
#


class SpineSlicerUS(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("SpineSlicerUS")
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Ultrasound")]
        self.parent.dependencies = ["VolumeResliceDriver"]  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Tamas Ungi (Queen's University)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#SpineSlicerUS">module documentation</a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # SpineSlicerUS sample 1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="SpineSlicerUS",
        sampleName="SpineUS_Sample1",
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, "SpineSlicerUS.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="SpineUS_Sample1.nrrd",
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        # This node name will be used when the data set is loaded
        nodeNames="SpineUS_Sample1",
    )

    # SpineSlicerUS sample 2
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="SpineSlicerUS",
        sampleName="SpineUS_Sample2",
        thumbnailFileName=os.path.join(iconsPath, "SpineSlicerUS.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames="SpineUS_Sample2.nrrd",
        checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        # This node name will be used when the data set is loaded
        nodeNames="SpineUS_Sample2",
    )


#
# SpineSlicerUSParameterNode
#


@parameterNodeWrapper
class SpineSlicerUSParameterNode:
    """
    The parameters needed by module.
    """
    inputVolume: vtkMRMLScalarVolumeNode
    imageToReference: vtkMRMLLinearTransformNode
    predictionToReference: vtkMRMLLinearTransformNode
    predictionVolume: vtkMRMLScalarVolumeNode
    predictionLabelMapVolume: vtkMRMLLabelMapVolumeNode
    recordPredictionsAsLabelMap: bool = False
    reconstructorNode: vtkMRMLVolumeReconstructionNode
    plusConnectorNode: vtkMRMLIGTLConnectorNode
    predictionConnectorNode: vtkMRMLIGTLConnectorNode
    blurSigma: Annotated[float, WithinRange(0, 5)] = 0.5
    reconstructedVolume: vtkMRMLScalarVolumeNode
    opacityThreshold: Annotated[int, WithinRange(-100, 200)] = 60
    invertThreshold: bool = False
    showKidney: bool = True  # Legacy parameter name; UI label presents this as Spine (Class 1).
    sequenceBrowserNode: vtkMRMLSequenceBrowserNode
    checkpointDescription: str = ""

#
# SpineSlicerUSWidget
#

class SpineSlicerUSWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """
    
    LAYOUT_2D3D = 601

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None
        
        self.displayedReconstructedVolume = None

        # for debugging
        slicer.mymod = self

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/SpineSlicerUS.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = SpineSlicerUSLogic()
        self.logic.setup()

        # Ensure any newly added qMRML widgets receive the MRML scene
        for widgetName in [
            "inputVolumeSelector",
            "predictionVolumeSelector",
            "probeToReferenceSelector",
            "reconstructorNodeSelector",
        ]:
            if hasattr(self.ui, widgetName):
                w = getattr(self.ui, widgetName)
                if hasattr(w, "setMRMLScene"):
                    w.setMRMLScene(slicer.mrmlScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartImportEvent, self.onSceneStartImport)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)

        # UI widget connections
        self.ui.startOpenIGTLinkButton.connect("toggled(bool)", self.onOpenIGTLinkButton)
        self.ui.applyButton.connect("clicked(bool)", self.onReconstructionButton)
        self.ui.volumeOpacitySlider.connect("valueChanged(int)", self.onVolumeOpacitySlider)
        self.ui.setRoiButton.connect("clicked(bool)", self.onSetRoiButton)
        self.ui.blurButton.connect("clicked()", self.onBlurButton)
        self.ui.recordPredictionsAsLabelMapButton.connect("toggled(bool)", self.onRecordPredictionsAsLabelMapButton)

        # Connect segmentation visualization checkbox (single binary segmentation)
        if hasattr(self.ui, 'showKidneyCheckBox'):
            self.ui.showKidneyCheckBox.connect('toggled(bool)', self.onSegmentationToggled)
        
        # Connect sequence recording controls
        self.ui.initializeRecordingButton.connect('clicked(bool)', self.onInitializeRecordingButton)
        self.ui.saveRecordingButton.connect('clicked(bool)', self.onSaveRecordingButton)
        
        # Set default output folder if not already set
        if hasattr(self.ui, 'outputFolderPathLineEdit'):
            if not self.ui.outputFolderPathLineEdit.currentPath:
                defaultPath = os.path.join(os.path.expanduser("~"), "Documents", "SpineUSRecordings")
                self.ui.outputFolderPathLineEdit.currentPath = defaultPath
       
        # Add custom layout
        self.addCustomLayouts()
        slicer.app.layoutManager().setLayout(self.LAYOUT_2D3D)
        slicer.app.layoutManager().sliceWidget("Red").sliceController().setSliceVisible(True)
        for viewNode in slicer.util.getNodesByClass("vtkMRMLAbstractViewNode"):
            viewNode.SetOrientationMarkerType(slicer.vtkMRMLAbstractViewNode.OrientationMarkerTypeHuman)
        
        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()
        
        # Autofill known scene nodes but keep manual selectors available.
        self.autoFillKnownSceneNodes()
        
        # Collapse DataProbe widget
        mw = slicer.util.mainWindow()
        if mw:
            w = slicer.util.findChild(mw, "DataProbeCollapsibleWidget")
            if w:
                w.collapsed = True
    
    def addCustomLayouts(self):
        layout2D3D = \
        """
        <layout type="horizontal" split="true">
            <item splitSize="500">
            <view class="vtkMRMLViewNode" singletontag="1">
                <property name="viewlabel" action="default">1</property>
            </view>
            </item>
            <item splitSize="500">
            <view class="vtkMRMLSliceNode" singletontag="Red">
                <property name="orientation" action="default">Axial</property>
                <property name="viewlabel" action="default">R</property>
                <property name="viewcolor" action="default">#F34A33</property>
            </view>
            </item>
        </layout>
        """
         
        layoutManager = slicer.app.layoutManager()
        if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_2D3D, layout2D3D):
            layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_2D3D, layout2D3D)
        
        # Add button to layout selector toolbar for this custom layout
        viewToolBar = slicer.util.mainWindow().findChild("QToolBar", "ViewToolBar")
        layoutMenu = viewToolBar.widgetForAction(viewToolBar.actions()[0]).menu()
        layoutSwitchActionParent = layoutMenu  # use `layoutMenu` to add inside layout list, use `viewToolBar` to add next the standard layout list
        layoutSwitchAction = layoutSwitchActionParent.addAction("3D-2D") # add inside layout list
        layoutSwitchAction.setData(self.LAYOUT_2D3D)
        layoutSwitchAction.setIcon(qt.QIcon(":Icons/Go.png"))
        layoutSwitchAction.setToolTip("3D and slice view")
    
    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        # stop volume reconstruction if running
        if self.logic and self.logic.reconstructing:
            self.logic.stopVolumeReconstruction()
        
        # stop OpenIGTLink connections if running
        if self._parameterNode:
            if self._parameterNode.plusConnectorNode:
                self._parameterNode.plusConnectorNode.Stop()
            if self._parameterNode.predictionConnectorNode:
                self._parameterNode.predictionConnectorNode.Stop()
        if self.logic:
            self.logic._removePredictionVolumeObserver()
        
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()
        # Refresh defaults from scene without overriding user-selected nodes.
        self.autoFillKnownSceneNodes()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._onParameterNodeModified)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def onSceneStartImport(self, caller, event) -> None:
        if self.parent.isEntered:
            logging.info("Scene import started: preserving existing hierarchy for recorded-sequence workflows.")
    
    def onSceneEndImport(self, caller, event) -> None:
        if self.parent.isEntered:
            self.logic.setup()
            self.initializeParameterNode()
            self.autoFillKnownSceneNodes()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())
    
    def autoFillKnownSceneNodes(self) -> None:
        """Assign defaults from known recorded-scene names without overriding manual selections."""
        if not hasattr(self, '_parameterNode') or not self._parameterNode or not self.logic:
            return

        parameterNode = self._parameterNode
        nodeCandidates = {
            "inputVolume": [self.logic.IMAGE_IMAGE],
            "predictionVolume": [self.logic.PREDICTION],
            "predictionLabelMapVolume": [self.logic.PREDICTION_LABELMAP],
            # ProbeToReference is primary; ImageToProbe and ImageToReference are legacy alternatives
            "imageToReference": [self.logic.PROBE_TO_REFERENCE, self.logic.IMAGE_TO_PROBE, self.logic.IMAGE_TO_REFERENCE],
            "predictionToReference": [self.logic.PREDICTION_TO_REFERENCE],
            "reconstructorNode": [self.logic.RECONSTRUCTOR_NODE],
            "reconstructedVolume": [self.logic.RECONSTRUCTED_VOLUME],
        }

        for parameterName, candidateNames in nodeCandidates.items():
            if getattr(parameterNode, parameterName):
                continue
            node = self.logic.getFirstNodeByNames(candidateNames)
            if node:
                setattr(parameterNode, parameterName, node)
        
    def setParameterNode(self, inputParameterNode: Optional[SpineSlicerUSParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._onParameterNodeModified)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._onParameterNodeModified)
            self._onParameterNodeModified()

    def _onParameterNodeModified(self, caller=None, event=None) -> None:
        """
        Update GUI based on parameter node changes.
        """
        # Update slice display with input volume
        if self._parameterNode and self._parameterNode.inputVolume:
            slicer.util.setSliceViewerLayers(background=self._parameterNode.inputVolume, fit=True)
            resliceDriverLogic = slicer.modules.volumereslicedriver.logic()
            # Get red slice node
            layoutManager = slicer.app.layoutManager()
            sliceWidget = layoutManager.sliceWidget("Red")
            sliceNode = sliceWidget.mrmlSliceNode()

            # Update slice using reslice driver
            resliceDriverLogic.SetDriverForSlice(self._parameterNode.inputVolume.GetID(), sliceNode)
            # Do not override slice orientation/rotation here.
            # Recorded sequences may already have the desired slice orientation set.

            # Fit slice to background
            sliceWidget.sliceController().fitSliceToBackground()

        # Update volume reconstruction button
        if self._parameterNode and self._parameterNode.inputVolume and self._parameterNode.predictionVolume and self._parameterNode.reconstructorNode:
            if self.logic.reconstructing:
                self.ui.applyButton.text = _("Stop volume reconstruction")
                self.ui.applyButton.toolTip = _("Stop volume reconstruction")
                self.ui.applyButton.checked = True
            else:
                self.ui.applyButton.text = _("Start volume reconstruction")
                self.ui.applyButton.toolTip = _("Start volume reconstruction")
                self.ui.applyButton.checked = False
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select input nodes to enable volume reconstruction")
            self.ui.applyButton.enabled = False

        if self._parameterNode:
            recordAsLabelMap = bool(self._parameterNode.recordPredictionsAsLabelMap)
            self.ui.recordPredictionsAsLabelMapButton.checked = recordAsLabelMap
            if recordAsLabelMap:
                self.ui.recordPredictionsAsLabelMapButton.text = _("Stop LabelMap Recording")
                self.ui.recordPredictionsAsLabelMapButton.toolTip = _("Disable labelmap prediction recording")
            else:
                self.ui.recordPredictionsAsLabelMapButton.text = _("Record Predictions as LabelMap")
                self.ui.recordPredictionsAsLabelMapButton.toolTip = _("Enable labelmap prediction recording")
            self.logic._setPredictionVolumeObserver(self._parameterNode.predictionVolume)
        
        # Update opacity threshold slider and segmentation visualization
        vrLogic = slicer.modules.volumerendering.logic()
        if self._parameterNode and self._parameterNode.reconstructedVolume:
            self.ui.volumeOpacitySlider.enabled = True
            # Update visibility of volumes
            if self.displayedReconstructedVolume and self.displayedReconstructedVolume != self._parameterNode.reconstructedVolume:
                previousDisplayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(self.displayedReconstructedVolume)
                if previousDisplayNode:
                    previousDisplayNode.SetVisibility(False)
            self.displayedReconstructedVolume = self._parameterNode.reconstructedVolume
            currentDisplayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(self.displayedReconstructedVolume)
            if currentDisplayNode and self.logic.hasValidImageData(self.displayedReconstructedVolume):
                currentDisplayNode.SetVisibility(True)

            # Update segmentation visualization when parameter node changes
            if hasattr(self._parameterNode, 'showKidney') and self.logic.hasValidImageData(self._parameterNode.reconstructedVolume):
                self.logic.updateSegmentationVisualization(
                    self._parameterNode.reconstructedVolume,
                    self._parameterNode.showKidney,
                )
        else:
            self.ui.volumeOpacitySlider.enabled = False
    
    def onOpenIGTLinkButton(self, checked: bool) -> None:
        parameterNode = self._parameterNode
        if not parameterNode.plusConnectorNode or not parameterNode.predictionConnectorNode:
            logging.warning("OpenIGTLink connectors are not selected/found. Select them in the scene first.")
            self.ui.startOpenIGTLinkButton.checked = False
            return
        if checked:
            parameterNode.plusConnectorNode.Start()
            parameterNode.predictionConnectorNode.Start()
        else:
            parameterNode.plusConnectorNode.Stop()
            parameterNode.predictionConnectorNode.Stop()
    
    def onReconstructionButton(self) -> None:
        """Run processing when user clicks button."""
        # Start volume reconstruction if not already started. Stop otherwise.
        
        if self.logic.reconstructing:
            self.ui.applyButton.text = _("Start volume reconstruction")
            self.ui.applyButton.toolTip = _("Start volume reconstruction")
            self.ui.applyButton.checked = False
            self.logic.stopVolumeReconstruction()
        else:
            self.ui.applyButton.text = _("Stop volume reconstruction")
            self.ui.applyButton.toolTip = _("Stop volume reconstruction")
            self.ui.applyButton.checked = True
            self.logic.startVolumeReconstruction()
    
    def onVolumeOpacitySlider(self, value: int) -> None:
        """Update volume rendering opacity threshold."""
        if self._parameterNode and self._parameterNode.reconstructedVolume:
            self.logic.setVolumeRenderingProperty(self._parameterNode.reconstructedVolume, window=200, level=(255 - value))
    
    def onSetRoiButton(self) -> None:
        """
        Center the volume reconstruction ROI on the current ultrasound image (in world space).
        """
        self.logic.resetRoiAndTargetsBasedOnImage()

    def onBlurButton(self) -> None:
        if self._parameterNode and self._parameterNode.reconstructedVolume:
            outputVolume = self.logic.blurVolume(self._parameterNode.reconstructedVolume, self._parameterNode.blurSigma)

            # Set volume property to MR-Default
            vrLogic = slicer.modules.volumerendering.logic()
            outputDisplayNode = vrLogic.CreateDefaultVolumeRenderingNodes(outputVolume)
            outputDisplayNode.GetVolumePropertyNode().Copy(vrLogic.GetPresetByName("MR-Default"))
            outputDisplayNode.SetVisibility(True)

            if self._parameterNode.inputVolume:
                # Change slice view back to Image_Image and reslice
                slicer.util.setSliceViewerLayers(background=self._parameterNode.inputVolume, fit=True)
                resliceDriverLogic = slicer.modules.volumereslicedriver.logic()

                # Get red slice node
                layoutManager = slicer.app.layoutManager()
                sliceWidget = layoutManager.sliceWidget("Red")
                sliceNode = sliceWidget.mrmlSliceNode()

                # Update slice using reslice driver
                resliceDriverLogic.SetDriverForSlice(self._parameterNode.inputVolume.GetID(), sliceNode)
                resliceDriverLogic.SetModeForSlice(resliceDriverLogic.MODE_TRANSVERSE, sliceNode)

                # Fit slice to background
                sliceWidget.sliceController().fitSliceToBackground()

            # Set blurred volume as active volume and hide the original volume
            inputDisplayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(self._parameterNode.reconstructedVolume)
            inputDisplayNode.SetVisibility(False)
            self._parameterNode.reconstructedVolume = outputVolume

    def onSegmentationToggled(self, checked):
        """Update volume rendering when segmentation visibility is toggled."""
        if self._parameterNode and self._parameterNode.reconstructedVolume:
            self.logic.updateSegmentationVisualization(
                self._parameterNode.reconstructedVolume,
                self._parameterNode.showKidney,
            )

    def onRecordPredictionsAsLabelMapButton(self, checked: bool) -> None:
        if not self._parameterNode:
            return
        self._parameterNode.recordPredictionsAsLabelMap = bool(checked)
        if checked:
            self.logic.syncPredictionToLabelMapVolume(force=True)
            self.logic.ensurePredictionLabelMapSequenceNode()
        self._onParameterNodeModified()
    
    def _getCurrentSequenceName(self) -> str:
        """3-digit participant id, e.g. '001'."""
        participantNum = self.ui.patientNumberSpinBox.value
        return f"{participantNum:03d}"

    def onInitializeRecordingButton(self):
        """Initialize the sequence browser and proxies for the current participant."""
        print("[Initialize Recording] Button pressed")
        if not self._parameterNode:
            msg = "Parameter node missing; attempting to initialize now"
            print(f"[Initialize Recording] {msg}")
            logging.warning(msg)
            try:
                self.initializeParameterNode()
            except Exception as e:
                err = f"Failed to initialize parameter node: {e}"
                print(f"[Initialize Recording] {err}")
                logging.error(err)
            if not self._parameterNode:
                err = "Parameter node is not available. Try reloading the module."
                print(f"[Initialize Recording] {err}")
                logging.error(err)
                return
        
        imageStream = self.logic.getFirstNodeByNames([self.logic.IMAGE_IMAGE], "vtkMRMLScalarVolumeNode")
        if not imageStream and self._parameterNode.inputVolume:
            imageStream = self._parameterNode.inputVolume
        if not imageStream:
            msg = "Cannot find ultrasound volume 'Image_Image'. Select it as input image or load the recording scene."
            print(f"[Initialize Recording] {msg}")
            logging.warning(msg)
            return
        
        sequenceName = self._getCurrentSequenceName()
        print(f"[Initialize Recording] Creating sequence browser: {sequenceName}")
        
        self.logic.createAndConfigureSequenceBrowser(sequenceName)
        
        # Connect sequence browser widget to the new node
        self._updateSequenceBrowserWidget()
        
        msg = f"Recording sequence '{sequenceName}' initialized and ready for recording"
        print(f"[Initialize Recording] {msg}")
        logging.info(msg)
    
    def _updateSequenceBrowserWidget(self):
        """Connect the sequence browser widgets to the current sequence browser node."""
        if not self._parameterNode or not self._parameterNode.sequenceBrowserNode:
            return
        
        sequenceBrowserNode = self._parameterNode.sequenceBrowserNode
        
        if hasattr(self.ui, 'sequenceBrowserPlayWidget'):
            self.ui.sequenceBrowserPlayWidget.setMRMLSequenceBrowserNode(sequenceBrowserNode)
        if hasattr(self.ui, 'sequenceBrowserSeekWidget'):
            self.ui.sequenceBrowserSeekWidget.setMRMLSequenceBrowserNode(sequenceBrowserNode)
    
    def onSaveRecordingButton(self):
        """Save the current recording to disk."""
        print("[Save Recording] Button pressed")
        if not self._parameterNode or not self._parameterNode.sequenceBrowserNode:
            msg = "No active recording. Please initialize and record a sequence first."
            print(f"[Save Recording] {msg}")
            logging.warning(msg)
            return
        
        # Get sequence browser and check if it has recorded data
        sequenceBrowserNode = self._parameterNode.sequenceBrowserNode
        synchronizedNodes = vtk.vtkCollection()
        sequenceBrowserNode.GetSynchronizedSequenceNodes(synchronizedNodes, True)
        
        if synchronizedNodes.GetNumberOfItems() == 0:
            msg = "Sequence browser has no synchronized nodes to save."
            print(f"[Save Recording] {msg}")
            logging.warning(msg)
            return

        # Stop recording before saving to avoid partial writes
        try:
            self.logic.stopSequenceRecording()
        except Exception:
            pass

        # Verify we actually have recorded frames (not just configured proxies)
        maxFrames = 0
        for i in range(synchronizedNodes.GetNumberOfItems()):
            seqNode = synchronizedNodes.GetItemAsObject(i)
            if not seqNode:
                continue
            try:
                if hasattr(seqNode, "GetNumberOfDataNodes"):
                    maxFrames = max(maxFrames, int(seqNode.GetNumberOfDataNodes()))
            except Exception:
                continue
        if maxFrames <= 0:
            msg = "No frames recorded yet. Please record a sequence before saving."
            print(f"[Save Recording] {msg}")
            logging.warning(msg)
            return
        
        sequenceName = self._getCurrentSequenceName()
        
        # Get output folder from UI selector, or use default
        if hasattr(self.ui, 'outputFolderPathLineEdit') and self.ui.outputFolderPathLineEdit.currentPath:
            baseDir = self.ui.outputFolderPathLineEdit.currentPath
        else:
            homeDir = os.path.expanduser("~")
            baseDir = os.path.join(homeDir, "Documents", "SpineUSRecordings")
        
        participantId = sequenceName
        saveDir = os.path.join(baseDir, participantId)
        
        # Create directory if it doesn't exist
        if not os.path.exists(saveDir):
            os.makedirs(saveDir)
        
        try:
            # Save sequence browser node
            sequenceFilename = os.path.join(saveDir, f"{sequenceName}.mrml")
            slicer.util.saveNode(sequenceBrowserNode, sequenceFilename)

            # Save all synchronized sequence nodes with consistent naming
            recordedProxyNames = []
            for i in range(synchronizedNodes.GetNumberOfItems()):
                sequenceNode = synchronizedNodes.GetItemAsObject(i)
                if sequenceNode:
                    nodeName = sequenceNode.GetName()
                    recordedProxyNames.append(nodeName)
                    nodeFilename = os.path.join(saveDir, f"{sequenceName}_{nodeName}.seq.nrrd")
                    slicer.util.saveNode(sequenceNode, nodeFilename)

            meta = {
                "sequenceName": sequenceName,
                "participantId": participantId,
                "savedAtUtc": datetime.now(timezone.utc).isoformat(),
                "outputDirectory": saveDir,
                "recordedProxies": recordedProxyNames,
                "recordPredictionsAsLabelMap": bool(self._parameterNode.recordPredictionsAsLabelMap),
                "maxFrames": maxFrames,
            }
            try:
                meta["slicerVersion"] = slicer.app.applicationVersion
            except Exception:
                pass
            metaPath = os.path.join(saveDir, f"{sequenceName}_metadata.json")
            with open(metaPath, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            msg = f"Recording '{sequenceName}' saved to {saveDir}"
            print(f"[Save Recording] {msg}")
            logging.info(msg)
        except Exception as e:
            err = f"Failed to save recording: {str(e)}"
            print(f"[Save Recording] {err}")
            logging.error(err)
    
#
# SpineSlicerUSLogic
#


class SpineSlicerUSLogic(ScriptedLoadableModuleLogic):
    """Logic for SpineSlicerUS volume reconstruction and visualization.

    This logic is agnostic to which segmentation checkpoint is used.
    It assumes that an external inference client:
    - Produces a prediction volume node named ``Prediction`` (or wired via the parameter node)
      containing a binary label map where 0=background and 1=target anatomy.
    - Streams that prediction into Slicer over OpenIGTLink.

    SpineSlicerUSLogic is responsible only for:
    - Creating/configuring MRML nodes (transforms, input/prediction volumes, reconstruction)
    - Driving live volume reconstruction from the prediction volume
    - Configuring binary volume rendering of the reconstructed volume
    """

    # transform names
    PROBE_TO_REFERENCE = "ProbeToReference"  # Primary probe transform (replaces ImageToReference)
    IMAGE_TO_PROBE = "ImageToProbe"  # Legacy: image-to-probe transform
    IMAGE_TO_REFERENCE = "ImageToReference"  # Legacy: image-to-reference transform
    PREDICTION_TO_REFERENCE = "PredToReference"

    # volume names
    IMAGE_IMAGE = "Image_Image"
    PREDICTION = "Prediction"
    PREDICTION_LABELMAP = "PredictionLabelMap"

    # reconstruction nodes
    RECONSTRUCTOR_NODE = "VolumeReconstruction"
    RECONSTRUCTED_VOLUME = "ReconstructedVolume"
    RECONSTRUCTION_ROI = "ReconstructionROI"

    # OpenIGTLink parameters
    PLUS_CONNECTOR = "PlusConnector"
    PREDICTION_CONNECTOR = "PredictionConnector"
    PLUS_CONNECTOR_PORT = 18944
    PREDICTION_CONNECTOR_PORT = 18945

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        
        self.reconstructing = False
        self._predictionVolumeObservedNode = None
        self._predictionVolumeObserverId = None
        self._updatingPredictionLabelMap = False

    def getParameterNode(self):
        return SpineSlicerUSParameterNode(super().getParameterNode())

    def getFirstNodeByNames(self, names, className=None):
        for nodeName in names:
            node = None
            try:
                node = slicer.util.getNode(nodeName)
            except Exception:
                node = None
            if not node:
                continue
            if className and not node.IsA(className):
                continue
            return node
        return None

    def _getOrCreateNode(self, parameterNode, parameterName, className, primaryName, aliases=None, initializer=None):
        aliases = aliases or []
        node = getattr(parameterNode, parameterName)
        created = False

        if not node:
            node = self.getFirstNodeByNames([primaryName] + aliases, className)
        if not node:
            node = slicer.mrmlScene.AddNewNodeByClass(className, primaryName)
            created = True
            if initializer:
                initializer(node)

        if node:
            setattr(parameterNode, parameterName, node)
        return node, created

    def setup(self):
        # Manual-node workflow: only predictionVolume is auto-created if missing.
        parameterNode = self.getParameterNode()

        parameterNode.imageToReference = parameterNode.imageToReference or self.getFirstNodeByNames(
            [self.PROBE_TO_REFERENCE, self.IMAGE_TO_PROBE, self.IMAGE_TO_REFERENCE], "vtkMRMLLinearTransformNode"
        )
        parameterNode.inputVolume = parameterNode.inputVolume or self.getFirstNodeByNames(
            [self.IMAGE_IMAGE], "vtkMRMLScalarVolumeNode"
        )
        predictionToReference = parameterNode.predictionToReference or self.getFirstNodeByNames(
            [self.PREDICTION_TO_REFERENCE], "vtkMRMLLinearTransformNode"
        )
        if not predictionToReference:
            predictionToReference = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode", self.PREDICTION_TO_REFERENCE
            )
            if not predictionToReference.GetParentTransformNode():
                parentTf = parameterNode.imageToReference
                if parentTf:
                    predictionToReference.SetAndObserveTransformNodeID(parentTf.GetID())
            logging.info("Auto-created missing prediction transform '%s'.", self.PREDICTION_TO_REFERENCE)
        parameterNode.predictionToReference = predictionToReference

        predictionVolume = parameterNode.predictionVolume or self.getFirstNodeByNames(
            [self.PREDICTION], "vtkMRMLScalarVolumeNode"
        )
        predictionVolumeCreated = False
        if not predictionVolume:
            predictionVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.PREDICTION)
            predictionVolume.CreateDefaultDisplayNodes()
            predictionArray = np.zeros((1, 512, 512), dtype="uint8")
            slicer.util.updateVolumeFromArray(predictionVolume, predictionArray)
            predictionVolumeCreated = True
            logging.info("Auto-created missing prediction volume '%s'.", self.PREDICTION)
        parameterNode.predictionVolume = predictionVolume
        if predictionVolumeCreated and parameterNode.predictionToReference and not predictionVolume.GetParentTransformNode():
            predictionVolume.SetAndObserveTransformNodeID(parameterNode.predictionToReference.GetID())

        predictionLabelMap = parameterNode.predictionLabelMapVolume or self.getFirstNodeByNames(
            [self.PREDICTION_LABELMAP], "vtkMRMLLabelMapVolumeNode"
        )
        if not predictionLabelMap:
            predictionLabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", self.PREDICTION_LABELMAP)
            predictionLabelMap.CreateDefaultDisplayNodes()
            labelMapArray = np.zeros((1, 512, 512), dtype="uint8")
            slicer.util.updateVolumeFromArray(predictionLabelMap, labelMapArray)
            logging.info("Auto-created missing prediction labelmap '%s'.", self.PREDICTION_LABELMAP)
        parameterNode.predictionLabelMapVolume = predictionLabelMap
        if parameterNode.predictionToReference and predictionLabelMap and not predictionLabelMap.GetParentTransformNode():
            predictionLabelMap.SetAndObserveTransformNodeID(parameterNode.predictionToReference.GetID())

        self._setPredictionVolumeObserver(parameterNode.predictionVolume)

        parameterNode.reconstructedVolume = parameterNode.reconstructedVolume or self.getFirstNodeByNames(
            [self.RECONSTRUCTED_VOLUME], "vtkMRMLScalarVolumeNode"
        )
        parameterNode.reconstructorNode = parameterNode.reconstructorNode or self.getFirstNodeByNames(
            [self.RECONSTRUCTOR_NODE], "vtkMRMLVolumeReconstructionNode"
        )

        if not parameterNode.reconstructedVolume:
            parameterNode.reconstructedVolume = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode", self.RECONSTRUCTED_VOLUME
            )
            parameterNode.reconstructedVolume.CreateDefaultDisplayNodes()

        if not parameterNode.reconstructorNode:
            parameterNode.reconstructorNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLVolumeReconstructionNode", self.RECONSTRUCTOR_NODE
            )
            parameterNode.reconstructorNode.SetLiveVolumeReconstruction(True)
            parameterNode.reconstructorNode.SetInterpolationMode(1)  # linear
            logging.info("Auto-created missing volume reconstruction node '%s'.", self.RECONSTRUCTOR_NODE)

        if parameterNode.reconstructedVolume:
            volRenLogic = slicer.modules.volumerendering.logic()
            reconstructedDisplay = volRenLogic.GetFirstVolumeRenderingDisplayNode(parameterNode.reconstructedVolume)
            if not reconstructedDisplay:
                reconstructedDisplay = volRenLogic.CreateDefaultVolumeRenderingNodes(parameterNode.reconstructedVolume)
            if self.hasValidImageData(parameterNode.reconstructedVolume):
                reconstructedDisplay.SetVisibility(True)
                reconstructedDisplay.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName("MR-Default"))

        if parameterNode.reconstructorNode:
            parameterNode.reconstructorNode.SetLiveVolumeReconstruction(True)
            parameterNode.reconstructorNode.SetInterpolationMode(1)  # linear
            if parameterNode.predictionVolume and not parameterNode.reconstructorNode.GetInputVolumeNode():
                parameterNode.reconstructorNode.SetAndObserveInputVolumeNode(parameterNode.predictionVolume)
            if parameterNode.reconstructedVolume and not parameterNode.reconstructorNode.GetOutputVolumeNode():
                parameterNode.reconstructorNode.SetAndObserveOutputVolumeNode(parameterNode.reconstructedVolume)
            if not parameterNode.reconstructorNode.GetInputROINode():
                roiNode = self.getFirstNodeByNames([self.RECONSTRUCTION_ROI], "vtkMRMLMarkupsROINode")
                if not roiNode:
                    roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", self.RECONSTRUCTION_ROI)
                    roiNode.SetSize((250, 250, 350))
                    roiNode.SetDisplayVisibility(False)
                parameterNode.reconstructorNode.SetAndObserveInputROINode(roiNode)

        missingManualNodes = []
        for parameterName in [
            "imageToReference",
            "inputVolume",
            "predictionToReference",
            "reconstructedVolume",
            "reconstructorNode",
        ]:
            if not getattr(parameterNode, parameterName):
                missingManualNodes.append(parameterName)
        if missingManualNodes:
            logging.warning(
                "Manual scene nodes not found (not auto-created): %s",
                ", ".join(missingManualNodes),
            )

        self.setupOpenIgtLink()

    def _removePredictionVolumeObserver(self):
        if self._predictionVolumeObservedNode and self._predictionVolumeObserverId:
            try:
                self._predictionVolumeObservedNode.RemoveObserver(self._predictionVolumeObserverId)
            except RuntimeError:
                pass
        self._predictionVolumeObservedNode = None
        self._predictionVolumeObserverId = None

    def _setPredictionVolumeObserver(self, predictionVolumeNode):
        self._removePredictionVolumeObserver()
        if not predictionVolumeNode:
            return
        self._predictionVolumeObserverId = predictionVolumeNode.AddObserver(
            vtk.vtkCommand.ModifiedEvent,
            self._onPredictionVolumeModified,
        )
        self._predictionVolumeObservedNode = predictionVolumeNode

    def _onPredictionVolumeModified(self, caller=None, event=None):
        self.syncPredictionToLabelMapVolume(force=False)

    def hasValidImageData(self, volumeNode):
        if not volumeNode:
            return False
        imageData = volumeNode.GetImageData()
        return bool(imageData and imageData.GetPointData() and imageData.GetNumberOfPoints() > 0)

    def syncPredictionToLabelMapVolume(self, force=False):
        parameterNode = self.getParameterNode()
        if not parameterNode:
            return
        if not force and not bool(parameterNode.recordPredictionsAsLabelMap):
            return
        if self._updatingPredictionLabelMap:
            return
        if not parameterNode.predictionVolume or not parameterNode.predictionLabelMapVolume:
            return

        try:
            predictionArray = slicer.util.arrayFromVolume(parameterNode.predictionVolume)
        except Exception:
            return
        if predictionArray is None:
            return

        # Keep binary label semantics for labelmap downstream workflows.
        labelMapArray = (predictionArray > 0).astype(np.uint8)
        self._updatingPredictionLabelMap = True
        try:
            # Follow TorchSequenceSegmentation's labelmap geometry approach to keep labelmap headers consistent.
            volumesLogic = slicer.modules.volumes.logic()
            volumesLogic.CreateLabelVolumeFromVolume(
                slicer.mrmlScene, parameterNode.predictionLabelMapVolume, parameterNode.predictionVolume
            )
            targetArray = slicer.util.arrayFromVolume(parameterNode.predictionLabelMapVolume)
            if targetArray is None or targetArray.shape != labelMapArray.shape:
                slicer.util.updateVolumeFromArray(parameterNode.predictionLabelMapVolume, labelMapArray)
            else:
                np.copyto(targetArray, labelMapArray, casting="unsafe")
                slicer.util.arrayFromVolumeModified(parameterNode.predictionLabelMapVolume)
            if parameterNode.predictionToReference:
                parameterNode.predictionLabelMapVolume.SetAndObserveTransformNodeID(
                    parameterNode.predictionToReference.GetID()
                )
            parameterNode.predictionLabelMapVolume.Modified()
            self.ensurePredictionLabelMapSequenceNode()
        finally:
            self._updatingPredictionLabelMap = False

    def ensurePredictionLabelMapSequenceNode(self, sequenceBrowserNode=None):
        parameterNode = self.getParameterNode()
        if not parameterNode or not bool(parameterNode.recordPredictionsAsLabelMap):
            return False
        if not sequenceBrowserNode:
            sequenceBrowserNode = parameterNode.sequenceBrowserNode
        if not sequenceBrowserNode:
            return False

        predictionLabelMapVolume = parameterNode.predictionLabelMapVolume or self.getFirstNodeByNames(
            [self.PREDICTION_LABELMAP], "vtkMRMLLabelMapVolumeNode"
        )
        if not predictionLabelMapVolume:
            return False

        seqNode = sequenceBrowserNode.GetSequenceNode(predictionLabelMapVolume)
        createdNow = False
        if not seqNode:
            sequencesLogic = slicer.modules.sequences.logic()
            seqNode = sequencesLogic.AddSynchronizedNode(None, predictionLabelMapVolume, sequenceBrowserNode)
            createdNow = bool(seqNode)
        if not seqNode:
            return False

        sequenceBrowserNode.SetRecording(seqNode, True)
        if createdNow:
            sequenceBrowserNode.SaveProxyNodesState()
        return True
    
    def setupOpenIgtLink(self):
        parameterNode = self.getParameterNode()
        parameterNode.plusConnectorNode = parameterNode.plusConnectorNode or self.getFirstNodeByNames(
            [self.PLUS_CONNECTOR], "vtkMRMLIGTLConnectorNode"
        )
        parameterNode.predictionConnectorNode = parameterNode.predictionConnectorNode or self.getFirstNodeByNames(
            [self.PREDICTION_CONNECTOR], "vtkMRMLIGTLConnectorNode"
        )

        if not parameterNode.plusConnectorNode:
            logging.warning("PLUS connector '%s' not found (not auto-created).", self.PLUS_CONNECTOR)
        if not parameterNode.predictionConnectorNode:
            logging.warning("Prediction connector '%s' not found (not auto-created).", self.PREDICTION_CONNECTOR)
    
    def startVolumeReconstruction(self):
        """
        Start live volume reconstruction.
        """
        parameterNode = self.getParameterNode()
        if not parameterNode.reconstructorNode:
            logging.warning("Volume reconstruction node is not selected/found. Cannot start reconstruction.")
            return
        self.reconstructing = True
        reconstructionLogic = slicer.modules.volumereconstruction.logic()
        reconstructionLogic.StartLiveVolumeReconstruction(parameterNode.reconstructorNode)
        outputVolume = parameterNode.reconstructorNode.GetOutputVolumeNode()
        # Use binary segmentation visualization (single foreground label) only when output has image data.
        if self.hasValidImageData(outputVolume):
            self.updateSegmentationVisualization(
                outputVolume,
                parameterNode.showKidney,
            )
        parameterNode.reconstructedVolume = outputVolume
    
    def stopVolumeReconstruction(self):
        """
        Stop live volume reconstruction.
        """
        parameterNode = self.getParameterNode()
        self.reconstructing = False
        reconstructionLogic = slicer.modules.volumereconstruction.logic()
        reconstructionLogic.StopLiveVolumeReconstruction(parameterNode.reconstructorNode)
    
    def setVolumeRenderingProperty(self, volumeNode, window=255, level=127):
        volumeRenderingLogic = slicer.modules.volumerendering.logic()
        volumeRenderingDisplayNode = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)
        if not volumeRenderingDisplayNode:
            volumeRenderingDisplayNode = volumeRenderingLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
            
        upper = min(255 + window, level + window/2)
        lower = max(0 - window, level - window/2)

        if upper <= lower:
            upper = lower + 1  # Make sure the displayed intensity range is valid.

        p0 = lower
        p1 = lower + (upper - lower)*0.15
        p2 = lower + (upper - lower)*0.4
        p3 = upper

        opacityTransferFunction = vtk.vtkPiecewiseFunction()
        opacityTransferFunction.AddPoint(p0, 0.0)
        opacityTransferFunction.AddPoint(p1, 0.2)
        opacityTransferFunction.AddPoint(p2, 0.6)
        opacityTransferFunction.AddPoint(p3, 1)

        colorTransferFunction = vtk.vtkColorTransferFunction()
        colorTransferFunction.AddRGBPoint(p0, 0.20, 0.10, 0.00)
        colorTransferFunction.AddRGBPoint(p1, 0.65, 0.45, 0.15)
        colorTransferFunction.AddRGBPoint(p2, 0.85, 0.75, 0.55)
        colorTransferFunction.AddRGBPoint(p3, 1.00, 1.00, 0.80)

        volumeProperty = volumeRenderingDisplayNode.GetVolumePropertyNode().GetVolumeProperty()
        volumeProperty.SetColor(colorTransferFunction)
        volumeProperty.SetScalarOpacity(opacityTransferFunction)
        volumeProperty.ShadeOn()
        volumeProperty.SetInterpolationTypeToLinear()
    
    def updateSegmentationVisualization(self, volumeNode, visible=True):
        """
        Update volume rendering for a single-class segmentation using MR-Default preset.

        Assumes:
        - 0: Background (always transparent)
        - 255: Foreground target anatomy
        """
        if not volumeNode or not self.hasValidImageData(volumeNode):
            return

        volumeRenderingLogic = slicer.modules.volumerendering.logic()
        volumeRenderingDisplayNode = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)
        if not volumeRenderingDisplayNode:
            volumeRenderingDisplayNode = volumeRenderingLogic.CreateDefaultVolumeRenderingNodes(volumeNode)

        if not visible:
            volumeRenderingDisplayNode.SetVisibility(False)
            return

        # Match TorchSequenceSegmentation-style rendering by using the built-in MR preset.
        volumePropertyNode = volumeRenderingDisplayNode.GetVolumePropertyNode()
        if volumePropertyNode:
            volumePropertyNode.Copy(volumeRenderingLogic.GetPresetByName("MR-Default"))

        volumeRenderingDisplayNode.SetVisibility(True)
    
    def resetRoiAndTargetsBasedOnImage(self):
        """
        Get the current position of Image in RAS. Make sure volume reconstruction has a ROI node and it is centered in the image.
        """
        parameterNode = self.getParameterNode()
        if not parameterNode.reconstructorNode:
            logging.error("Reconstructor node is not set")
            return
        
        # Get the current position of Image in RAS
        imageNode = parameterNode.inputVolume
        if not imageNode:
            logging.warning("Cannot set ROI because input volume is not set")
            return
        
        # Get the center of the image
        imageBounds_Ras = np.zeros(6)
        imageNode.GetRASBounds(imageBounds_Ras)
        imageCenter_Ras = np.zeros(3)
        for i in range(3):
            imageCenter_Ras[i] = (imageBounds_Ras[i*2] + imageBounds_Ras[i*2+1]) / 2
        
        # Set the center of the ROI to the center of the image
        roiNode = parameterNode.reconstructorNode.GetInputROINode()
        if not roiNode:
            logging.warning("No ROI node found in volume reconstruction node")
            return
        roiNode.SetCenterWorld(imageCenter_Ras)

    def blurVolume(self, inputVolume, sigma):
        parameterNode = self.getParameterNode()

        # Set CLI parameters
        inputVolumeName = inputVolume.GetName()
        outputVolumeName = f"{inputVolumeName}_blurred_{sigma:.2f}"
        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", outputVolumeName)
        parameters = {
            "inputVolume": inputVolume, 
            "outputVolume": outputVolume,
            "sigma": sigma
        }
        
        # Run CLI module
        gaussianBlur = slicer.modules.gaussianblurimagefilter
        cliNode = slicer.cli.runSync(gaussianBlur, None, parameters)

        # Process results
        if cliNode.GetStatus() & cliNode.ErrorsMask:
            errorText = cliNode.GetErrorText()
            logging.error(f"Error in GaussianBlurImageFilter: {errorText}")
            slicer.mrmlScene.RemoveNode(cliNode)
        else:
            slicer.mrmlScene.RemoveNode(cliNode)
            return outputVolume
    
    def createAndConfigureSequenceBrowser(self, sequenceName):
        """
        Create and configure a sequence browser for recording ultrasound sequences.
        Records ProbeToReference, ImageToProbe, Image_Image, PredToReference, and
        optionally PredictionLabelMap when labelmap recording is enabled.
        
        :param sequenceName: Name for the sequence (e.g., padded participant id)
        """
        parameterNode = self.getParameterNode()

        browserName = f"SequenceBrowser_{sequenceName}"
        sequenceBrowserNode = None
        try:
            sequenceBrowserNode = slicer.util.getNode(browserName)
            if sequenceBrowserNode and not sequenceBrowserNode.IsA("vtkMRMLSequenceBrowserNode"):
                sequenceBrowserNode = None
        except Exception:
            sequenceBrowserNode = None

        # Create a new sequence browser node if it doesn't exist
        if not sequenceBrowserNode:
            sequenceBrowserNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSequenceBrowserNode", browserName
            )
        
        # Get sequences logic
        sequencesLogic = slicer.modules.sequences.logic()
        
        # Track success of adding nodes
        successCount = 0
        expectedLabels = [
            self.PROBE_TO_REFERENCE,
            self.IMAGE_TO_PROBE,
            self.IMAGE_IMAGE,
            self.PREDICTION_TO_REFERENCE,
        ]
        if bool(parameterNode.recordPredictionsAsLabelMap):
            expectedLabels.append(self.PREDICTION_LABELMAP)
        failedLabels = []
        addedNodeIds = set()

        def add_proxy(node, label):
            nonlocal successCount
            if node:
                nodeId = node.GetID() if hasattr(node, "GetID") else None
                if nodeId and nodeId in addedNodeIds:
                    return
                try:
                    seqNode = sequencesLogic.AddSynchronizedNode(None, node, sequenceBrowserNode)
                    sequenceBrowserNode.SetRecording(seqNode, True)
                    successCount += 1
                    if nodeId:
                        addedNodeIds.add(nodeId)
                    logging.info(f"Added '{label}' proxy node to sequence browser")
                except Exception as e:
                    failedLabels.append(label)
                    logging.error(f"Failed to add '{label}' to sequence browser: {str(e)}")
            else:
                failedLabels.append(label)
                logging.warning(f"Node '{label}' not found or not set")

        probeToReference = self.getFirstNodeByNames([self.PROBE_TO_REFERENCE], "vtkMRMLLinearTransformNode")
        add_proxy(probeToReference, self.PROBE_TO_REFERENCE)
        imageToProbe = self.getFirstNodeByNames([self.IMAGE_TO_PROBE], "vtkMRMLLinearTransformNode")
        add_proxy(imageToProbe, self.IMAGE_TO_PROBE)
        imageImage = self.getFirstNodeByNames([self.IMAGE_IMAGE], "vtkMRMLScalarVolumeNode")
        add_proxy(imageImage, self.IMAGE_IMAGE)
        predictionToReference = parameterNode.predictionToReference or self.getFirstNodeByNames(
            [self.PREDICTION_TO_REFERENCE], "vtkMRMLLinearTransformNode"
        )
        add_proxy(predictionToReference, self.PREDICTION_TO_REFERENCE)
        if bool(parameterNode.recordPredictionsAsLabelMap):
            if self.ensurePredictionLabelMapSequenceNode(sequenceBrowserNode):
                successCount += 1
            else:
                failedLabels.append(self.PREDICTION_LABELMAP)

        
        # Store sequence browser in parameter node
        parameterNode.sequenceBrowserNode = sequenceBrowserNode

        # Log final status
        if failedLabels:
            msg = (
                f"Sequence browser '{sequenceName}' created with {successCount}/{len(expectedLabels)} "
                f"nodes. Failed or missing: {', '.join(failedLabels)}."
            )
            print(f"[Sequence Browser] {msg}")
            logging.warning(msg)
        else:
            msg = (
                f"Sequence browser '{sequenceName}' created successfully with all {successCount} proxy nodes: "
                f"{', '.join(expectedLabels)}."
            )
            print(f"[Sequence Browser] {msg}")
            logging.info(msg)
        
    def getSequenceBrowserNode(self):
        """Get the current sequence browser node."""
        parameterNode = self.getParameterNode()
        return parameterNode.sequenceBrowserNode
        
    def startSequenceRecording(self):
        """Start recording to the current sequence browser."""
        parameterNode = self.getParameterNode()
        sequenceBrowserNode = parameterNode.sequenceBrowserNode
        
        if not sequenceBrowserNode:
            raise RuntimeError("No active sequence browser node found")
        
        # Get all synchronized sequence nodes
        synchronizedNodes = vtk.vtkCollection()
        sequenceBrowserNode.GetSynchronizedSequenceNodes(synchronizedNodes, True)
        
        if synchronizedNodes.GetNumberOfItems() == 0:
            raise RuntimeError("No synchronized nodes found in sequence browser")
        
        # Set all synchronized sequence nodes to recording mode
        for i in range(synchronizedNodes.GetNumberOfItems()):
            sequenceNode = synchronizedNodes.GetItemAsObject(i)
            sequenceBrowserNode.SetRecording(sequenceNode, True)
        
        logging.info(f"Started sequence recording with {synchronizedNodes.GetNumberOfItems()} proxy nodes")
        
    def stopSequenceRecording(self):
        """Stop recording to the current sequence browser."""
        parameterNode = self.getParameterNode()
        if parameterNode.sequenceBrowserNode:
            # Set all synchronized sequence nodes to non-recording mode
            synchronizedNodes = vtk.vtkCollection()
            parameterNode.sequenceBrowserNode.GetSynchronizedSequenceNodes(synchronizedNodes, True)
            for i in range(synchronizedNodes.GetNumberOfItems()):
                sequenceNode = synchronizedNodes.GetItemAsObject(i)
                parameterNode.sequenceBrowserNode.SetRecording(sequenceNode, False)
            logging.info("Stopped sequence recording")


#
# SpineSlicerUSTest
#


class SpineSlicerUSTest(ScriptedLoadableModuleTest):
    """
    Basic smoke test for the SpineSlicerUS module.

    This does not exercise the full reconstruction pipeline (which depends on
    external OpenIGTLink streams), but ensures that the logic can be instantiated
    and that core MRML nodes are created without errors.
    """

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SpineSlicerUS_LogicSetup()

    def test_SpineSlicerUS_LogicSetup(self):
        logic = SpineSlicerUSLogic()
        logic.setup()
        parameterNode = logic.getParameterNode()
        self.assertIsNotNone(parameterNode.inputVolume)
        self.assertIsNotNone(parameterNode.predictionVolume)
        self.assertIsNotNone(parameterNode.predictionLabelMapVolume)
        self.assertFalse(parameterNode.recordPredictionsAsLabelMap)
        self.assertIsNotNone(parameterNode.reconstructorNode)
