import logging
import os
import qt
from typing import Annotated, Optional
import colorsys
import vtk
import random
import time
import slicer
import re
import csv
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode


#
# FracturedBoneSegmentation
#


class FracturedBoneSegmentation(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Fractured Bone Segmentation")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Segmentation")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Maia Zappia (Università degli Studi di Genova)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""Automatic segmentation of fractured bones from CT. See documentation at: <a href = "https://github.com/maia-zappia/FracturedBoneSegmentation">GitHub repository</a>

""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""This module was developed as part of a thesis project at the University of Genoa.
We thank the 3D Slicer developer community for providing the ScriptedLoadableModule template.


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

    # FracturedBoneSegmentation1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="FracturedBoneSegmentation",
        sampleName="FracturedBoneSegmentation1",
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, "FracturedBoneSegmentation1.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="FracturedBoneSegmentation1.nrrd",
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        # This node name will be used when the data set is loaded
        nodeNames="FracturedBoneSegmentation1",
    )

    # FracturedBoneSegmentation2
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="FracturedBoneSegmentation",
        sampleName="FracturedBoneSegmentation2",
        thumbnailFileName=os.path.join(iconsPath, "FracturedBoneSegmentation2.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames="FracturedBoneSegmentation2.nrrd",
        checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        # This node name will be used when the data set is loaded
        nodeNames="FracturedBoneSegmentation2",
    )


#
# FracturedBoneSegmentationParameterNode
#


@parameterNodeWrapper
class FracturedBoneSegmentationParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """

    inputVolume: vtkMRMLScalarVolumeNode
    imageThreshold: Annotated[float, WithinRange(-100, 500)] = 100
    invertThreshold: bool = False
    thresholdedVolume: vtkMRMLScalarVolumeNode
    invertedVolume: vtkMRMLScalarVolumeNode


#
# FracturedBoneSegmentationWidget
#


class FracturedBoneSegmentationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """
    segmentName = None

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = FracturedBoneSegmentationLogic()
        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/FracturedBoneSegmentation.ui"))
        self.layout.addWidget(uiWidget)
        self.uiWidget = uiWidget
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.ui.stackedWidget.setCurrentIndex(0)

        self.ui.openDicomImporter.clicked.connect(self.openDICOMModule)
        self.ui.segmentEditorButton.clicked.connect(self.openSegmentEditor)
        self.ui.autoSegmentationButton.clicked.connect(self.autoSegmentation)
        self.ui.blenderButton.clicked.connect(self.exportSegmentationAndOpenInBlender)
        self.ui.addButton.clicked.connect(self.perform_add_from_selected_table)
        self.ui.subButton.clicked.connect(self.perform_subtract_from_selected_table)
        self.ui.splitButton.clicked.connect(self.split_selected_segment_inplace_using_threshold_helper)
        self.ui.deleteButton.clicked.connect(self.delete_selected_segment)
        self.ui.videoButton.clicked.connect(self.prepare_screen_capture_module_from_ui_robust)


        # init source selector (works if hai aggiunto sourceVolumeSelector nella .ui)
        if hasattr(self.ui, "sourceVolumeSelector"):
            try:
                self.ui.sourceVolumeSelector.setMRMLScene(slicer.mrmlScene)
                firstVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
                if firstVolume:
                    self.ui.sourceVolumeSelector.setCurrentNode(firstVolume)
            except Exception:
                pass


        #progress bar
        self.progressBar = self.ui.progressBar
        self.progressBar.setVisible(False)


        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = FracturedBoneSegmentationLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        #slicer.util.infoDisplay("Welcome on Fractured Bone Segmentation! To start, load your dataset or choose one among the available sample datasets.")
        if hasattr(self, "setup_table_selection_callbacks"):
            try:
                self.setup_table_selection_callbacks()
            except Exception as e:
                print("setup_table_selection_callbacks() raised:", e)
        else:
            print("setup_table_selection_callbacks() non definito, skip.")

    def openDICOMModule(self):
        slicer.util.selectModule('DICOM')
        slicer.modules.dicom.widgetRepresentation().self().browserWidget.dicomBrowser.show()
        
    def openSegmentEditor(self):
        slicer.util.selectModule('SegmentEditor')
        #slicer.modules.dicom.widgetRepresentation().self().browserWidget.dicomBrowser.show()


    def sanitize_filename(self, s):
        # sostituisce caratteri non sicuri e spazi; mantiene underscore e -. 
        s = re.sub(r'[^A-Za-z0-9_. -]', '_', s)
        s = s.replace(' ', '_')
        return s

    def segmentation_to_csv(self, segNode=None, output_csv=None, use_extension_for_filename=True, ext='.stl'):
        """
        Crea un CSV con mapping tra filename (opzionale con estensione), nome segmento, colore (r,g,b) e hex.
        - segNode: vtkMRMLSegmentationNode (se None prende il primo nella scena)
        - output_csv: percorso completo del csv (se None viene salvato in ~/Desktop/colors.csv)
        - use_extension_for_filename: se True aggiunge ext al nome (utile perché Blender crea oggetti con il nome del file)
        - ext: estensione usata per il filename ('.stl' o '.obj')
        """
        if segNode is None:
            segNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if segNode is None:
                print("Nessun vtkMRMLSegmentationNode trovato nella scena.")
                return

        if output_csv is None:
            output_csv = os.path.expanduser(os.path.join("~", "Desktop", "slicer_segment_colors.csv"))

        segmentation = segNode.GetSegmentation()
        n = segmentation.GetNumberOfSegments()
        rows = []

        for i in range(n):
            segId = segmentation.GetNthSegmentID(i)
            seg = segmentation.GetSegment(segId)
            # nome visuale del segmento
            name = seg.GetName()
            # colore (r,g,b) in [0..1]
            try:
                r, g, b = seg.GetColor()
            except Exception:
                # fallback se API diversa
                color = seg.GetColor()
                r, g, b = float(color[0]), float(color[1]), float(color[2])
            # hex (RRGGBB)
            hexcode = "{:02X}{:02X}{:02X}".format(int(round(r*255)), int(round(g*255)), int(round(b*255)))
            # filename (sanitize) — vuoi che corrisponda ai file .stl che poi importerai in Blender
            safe_name = self.sanitize_filename(name)
            if use_extension_for_filename:
                filename = safe_name + ext
            else:
                filename = safe_name

            rows.append({
                'filename': filename,
                'segment_name': name,
                'r': "{:.6f}".format(r),
                'g': "{:.6f}".format(g),
                'b': "{:.6f}".format(b),
                'hex': '#' + hexcode
            })

        # create output folder if necessary
        outdir = os.path.dirname(output_csv)
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)

        # write CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['filename', 'segment_name', 'r', 'g', 'b', 'hex']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(f"Wrote CSV with {len(rows)} entries to: {output_csv}")
        return output_csv

    def autoSegmentation(self):
        import SegmentEditorEffects

        #show the progress bar
        self.progressBar.setVisible(True)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)
        self.progressBar.setFormat("%p%") 
        slicer.app.processEvents()

        #get the segment name in input     
        segmentName = self.ui.lineEdit.text
        if not segmentName.strip(): 
            slicer.util.warningDisplay("Insert the segment name", windowTitle = "Error") 
            self.progressBar.setVisible(False)
            return 

        #slicer.util.selectModule('SegmentEditor') #open the SegmentEditor
        #segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.progressBar.setValue(5)
        slicer.app.processEvents()

        #creation of the segmentation node
        timestamp = int(time.time())
        safe_segment_name = self.sanitize_filename(segmentName)
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode",
            f"Segmentation_{safe_segment_name}_{timestamp}"
        )

        #get the internal widget for the segment editor
        segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor

        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setSegmentationNode(segmentationNode)

        #masterVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        # read user-selected source volume from UI
        if hasattr(self.ui, "sourceVolumeSelector"):
            masterVolumeNode = self.ui.sourceVolumeSelector.currentNode()
        else:
            # fallback se non esiste il selector nella UI
            masterVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

        if masterVolumeNode is None:
            slicer.util.warningDisplay("Seleziona un source volume prima di avviare l'auto segmentation.", windowTitle="Errore")
            self.progressBar.setVisible(False)
            return

        segmentEditorWidget.setSourceVolumeNode(masterVolumeNode)
            
        #add an empty segment with the chosen name 
        segmentation = segmentationNode.GetSegmentation()
        segmentation.RemoveAllSegments()  # rimuove qualsiasi segmento precedente
        segmentation.AddEmptySegment("", segmentName)
        lastId = segmentation.GetNthSegmentID(segmentation.GetNumberOfSegments()-1)
        segmentEditorWidget.setCurrentSegmentID(lastId)
        #boneColor = [0.954, 0.839, 0.569]
        segment = segmentation.GetSegment(lastId)
        #segment.SetColor(boneColor)
        self.progressBar.setValue(15)
        slicer.app.processEvents()

        #set the threshold values
        segmentEditorWidget.setActiveEffectByName('Threshold')
        effect = segmentEditorWidget.activeEffect()
        minTh1 = self.ui.lineEdit_2.text
        if not minTh1.strip():
            minTh1 = 500
        #effect.setParameter('MinimumThreshold', str(1465.00))
        effect.setParameter('MinimumThreshold', str(minTh1))
        effect.setParameter('MaximumThreshold', str(1926.00))
        effect.self().onApply()
        slicer.app.processEvents()
        self.progressBar.setValue(25)
        currentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(str(segmentName))
        segmentEditorWidget.setCurrentSegmentID(currentId)

        #fragments separation
        segmentEditorWidget.setActiveEffectByName('Islands')
        effect = segmentEditorWidget.activeEffect()
        voxelsNum = self.ui.lineEdit_4.text
        if not voxelsNum.strip():
            voxelsNum = 100
        effect.setParameter('Operation', SegmentEditorEffects.SPLIT_ISLANDS_TO_SEGMENTS)
        #effect.setParameter('MinimumSize', '500')
        effect.setParameter('MinimumSize', voxelsNum)
        effect.self().onApply()
        #print(segmentation.GetNumberOfSegments())
        slicer.app.processEvents()
        for i in range(segmentation.GetNumberOfSegments()):
            segmentID = segmentation.GetNthSegmentID(i)
            newName = f'{segmentName} {i + 1}'
            segmentation.GetSegment(segmentID).SetName(newName)
            hue = float(i * 0.61803398875) % 1.0
            saturation = 0.55 + 0.3 * (i % 2) 
            value = 0.8 + 0.2 * (i % 2)
            r, g, b, = colorsys.hsv_to_rgb(hue, saturation, value)
            segmentation.GetSegment(segmentID).SetColor(r, g, b)

        self.progressBar.setValue(45)
        slicer.app.processEvents()

        # UPDATED: adjust minimum to 146.60
        segmentEditorWidget.setActiveEffectByName('Threshold')
        effect = segmentEditorWidget.activeEffect()
        minTh2 = self.ui.lineEdit_3.text
        if not minTh2.strip():
            minTh2 = 100
        #effect.setParameter('MinimumThreshold', str(146.60))
        effect.setParameter('MinimumThreshold', str(minTh2))
        effect.self().onUseForPaint()
        slicer.app.processEvents()

        #grow from seeds
        segmentEditorWidget.setActiveEffectByName('Grow from seeds')
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter('SeedLocalityFactor', '8')
        effect.self().onPreview()
        effect.self().onApply()
        slicer.app.processEvents()
        self.progressBar.setValue(70)

        #smoothing
        segmentEditorWidget.setActiveEffectByName('Smoothing')
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter('SmoothingMethod', 'GAUSSIAN')
        effect.setParameter('GaussianStandardDeviationMm', 0.5)
        segmentationNode = segmentEditorWidget.segmentationNode()
        numSegments = segmentationNode.GetSegmentation().GetNumberOfSegments()
        for i in range(numSegments):
            segmentID = segmentationNode.GetSegmentation().GetNthSegmentID(i)
            segmentEditorWidget.setCurrentSegmentID(segmentID)
            effect.self().onApply()
            slicer.app.processEvents()  
        self.progressBar.setValue(90)

        #enable Show3D and close the module
        segmentEditorWidget.setActiveEffectByName(None)
        displayNode = segmentationNode.GetDisplayNode()
        segmentationNode.CreateClosedSurfaceRepresentation()
        displayNode.SetSegmentVisibility3D(lastId, True)
        displayNode.SetVisibility2DFill(False)
        displayNode.SetVisibility2DOutline(True)
        slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()
        #slicer.util.selectModule('FracturedBoneSegmentation')
        self.ui.stackedWidget.setCurrentIndex(1)
        self.progressBar.setValue(100)
        slicer.app.processEvents()
        slicer.util.infoDisplay("Segmentation finished successfully!")

        #table update 
        self.onSegmentationNodeChanged(segmentationNode)

        self.progressBar.setVisible(False) 


        # --- salvataggio in DUE cartelle: "Fracture Reduction SB" e "Fracture Reduction VR" ---
        # percorso attuale (quello che avevi) — lo useremo per calcolare i due target sostituendo il nome della cartella
        _original_assets_folder = r"path"

        # target names da usare al posto di "Fracture Reduction"
        target_names = ["Fracture Reduction SB", "Fracture Reduction VR"]

        # funzione helper per ottenere il path target sostituendo la cartella 'Fracture Reduction'
        def _replace_folder_in_path(path, old_folder, new_folder):
            parts = path.split(os.path.sep)
            try:
                idx = parts.index(old_folder)
                parts[idx] = new_folder
                return os.path.sep.join(parts)
            except ValueError:
                # se non trova la cartella, prova una sostituzione stringa (fallback)
                return path.replace(old_folder, new_folder)

        # calcola i due root target e crea le sottocartelle <segmentName> in entrambe
        unity_targets = []
        for tname in target_names:
            target_root = _replace_folder_in_path(_original_assets_folder, "Fracture Reduction", tname)
            unity_folder = os.path.join(target_root, segmentName)
            os.makedirs(unity_folder, exist_ok=True)
            unity_targets.append(unity_folder)

        # salva il CSV in entrambe le cartelle e crea la sottocartella 'Video' affianco
        csv_paths = []
        for folder in unity_targets:
            csv_path = os.path.join(folder, "colors.csv")
            self.segmentation_to_csv(segmentationNode, csv_path)
            csv_paths.append(csv_path)

            # crea la sottocartella Video accanto al CSV (se non esiste)
            video_dir = self.create_video_subfolder_for_csv(csv_path)
            if video_dir:
                print(f"Cartella 'Video' creata o già esistente: {video_dir}")
            else:
                print(f"Impossibile creare la cartella 'Video' per: {csv_path}")

        self._last_saved_colors_csv = csv_paths[0]  # oppure csv_paths[-1]
        print("Memorizzato last_saved_colors_csv =", self._last_saved_colors_csv)
        print("CSV scritti in:", ", ".join(csv_paths))


    def create_video_subfolder_for_csv(self, csv_path_or_folder):
        """
        Crea (se non esiste) la sottocartella 'Video' nella stessa cartella
        dove si trova `csv_path_or_folder`. Se viene passato il path di un file
        (es. .../colors.csv) prende la sua directory; se viene passata già una
        directory la usa direttamente.
        Restituisce il path della cartella 'Video' creata o None in caso di errore.
        """
        try:
            if isinstance(csv_path_or_folder, str) and csv_path_or_folder.lower().endswith('.csv'):
                folder = os.path.dirname(csv_path_or_folder) or os.getcwd()
            else:
                folder = csv_path_or_folder or os.getcwd()
            video_folder = os.path.join(folder, "Video")
            os.makedirs(video_folder, exist_ok=True)
            return video_folder
        except Exception as e:
            print(f"[create_video_subfolder_for_csv] Impossibile creare '{csv_path_or_folder}/Video': {e}")
            return None



    def prepare_screen_capture_module_from_ui_robust(self):
        """
        1) seleziona Segmentations e disattiva la visibilità dei segmenti nelle main views
        2) seleziona ScreenCapture e imposta nell'ordine:
        - main view = Red
        - capture mode = Slice sweep
        - output type = Video
        - number of images = 220
        - output file name = axial.mp4
        - video length = 10 s
        NON preme Capture (lascia all'utente).
        Ritorna dict con sc_widget, sc_logic, desired_output_dir, successes, failures, exceptions.
        """
        import os
        import slicer
        from qt import Qt

        results = {"successes": [], "failures": [], "exceptions": []}
        def ok(msg):
            results["successes"].append(msg)
            print("[SC][OK]", msg)
        def fail(msg):
            results["failures"].append(msg)
            print("[SC][FAIL]", msg)
        def exc(ctx, e):
            s = f"{ctx}: {type(e).__name__}: {e}"
            results["exceptions"].append(s)
            print("[SC][EXC]", s)

        # ---------- helper ----------
        def setComboBoxByItemData(comboBox, targetData, role=qt.Qt.UserRole):
            for i in range(comboBox.count):
                if comboBox.itemData(i, role) == targetData:
                    comboBox.setCurrentIndex(i)
                    return True
            return False


        def get_red_slice_node():
            # prefer node by ID used in tests, fallback to layoutManager sliceWidget('Red')
            try:
                node = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
                if node:
                    return node
            except Exception:
                pass
            try:
                lm = slicer.app.layoutManager()
                sw = lm.sliceWidget("Red")
                if sw:
                    return sw.sliceLogic().GetSliceNode()
            except Exception:
                pass
            # fallback: try node named "Red"
            try:
                return slicer.util.getNode("Red")
            except Exception:
                return None

        # ---------- 1) disattiva segmentazioni ----------
        try:
            slicer.util.selectModule("Segmentations")
            slicer.app.processEvents()
            ok("selected_module_Segmentations")
        except Exception as e:
            exc("selectModule_Segmentations_failed", e)

        try:
            segNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSegmentationNode')
            if segNodes and segNodes.GetNumberOfItems() > 0:
                for i in range(segNodes.GetNumberOfItems()):
                    try:
                        segNode = segNodes.GetItemAsObject(i)
                        disp = segNode.GetDisplayNode() if hasattr(segNode, "GetDisplayNode") else None
                        if disp and hasattr(disp, "SetAllSegmentsVisibility"):
                            try:
                                disp.SetAllSegmentsVisibility(False)
                                ok(f"seg_display_hidden:{segNode.GetName()}")
                            except Exception as e:
                                exc("SetAllSegmentsVisibility_failed", e)
                        elif disp:
                            # fallback per id dei segmenti
                            try:
                                seg = segNode.GetSegmentation()
                                ids = seg.GetSegmentIDs()
                                try:
                                    n = ids.GetNumberOfValues()
                                    for j in range(n):
                                        sid = ids.GetValue(j)
                                        try:
                                            disp.SetSegmentVisibility(sid, 0)
                                        except Exception:
                                            pass
                                    ok(f"seg_display_hidden_iter_ids:{segNode.GetName()}")
                                except Exception:
                                    for sid in list(ids):
                                        try:
                                            disp.SetSegmentVisibility(sid, 0)
                                        except Exception:
                                            pass
                                    ok(f"seg_display_hidden_iterable_ids:{segNode.GetName()}")
                            except Exception as e:
                                exc("segmentation_iteration_failed", e)
                        else:
                            fail(f"no_display_node_for_segmentation:{getattr(segNode, 'GetName', lambda: '<no-name>')()}")
                    except Exception as e:
                        exc("processing_segmentation_node_failed", e)
            else:
                ok("no_segmentation_nodes_found")
        except Exception as e:
            exc("disable_segments_overall_failed", e)

        # ---------- 2) apri ScreenCapture ----------
        sc_widget = None
        sc_logic = None
        try:
            slicer.util.selectModule("ScreenCapture")
            slicer.app.processEvents()
            ok("selectModule_ScreenCapture_called")
        except Exception as e:
            exc("selectModule_ScreenCapture_failed", e)

        # get widget
        try:
            try:
                sc_widget = slicer.modules.screencapture.widgetRepresentation().self()
                ok("got_widget_via_widgetRepresentation.self()")
            except Exception:
                sc_widget = None
                exc("widgetRepresentation_failed", "inner")
                try:
                    mw = slicer.util.mainWindow()
                    for child in mw.findChildren(object):
                        try:
                            nm = child.objectName() if hasattr(child, "objectName") else ""
                            cls = child.metaObject().className() if hasattr(child, "metaObject") and child.metaObject() else ""
                            if ("ScreenCapture" in nm) or ("ScreenCapture" in cls) or ("screencapture" in nm.lower()):
                                sc_widget = child
                                ok("got_widget_via_mainWindow_search")
                                break
                        except Exception:
                            continue
                except Exception as e2:
                    exc("mainWindow_search_failed", e2)
        except Exception as e:
            exc("unexpected_widget_error", e)

        # get logic
        try:
            if 'ScreenCapture' in globals() and hasattr(ScreenCapture, "ScreenCaptureLogic"):
                try:
                    sc_logic = ScreenCapture.ScreenCaptureLogic()
                    ok("sc_logic_via_global_ScreenCapture")
                except Exception as e:
                    exc("sc_logic_global_instantiation_failed", e)
            else:
                try:
                    sc_logic = slicer.modules.screencapture.logic()
                    ok("sc_logic_via_module_logic()")
                except Exception as e:
                    sc_logic = None
                    exc("sc_logic_module_logic_failed", e)
        except Exception as e:
            sc_logic = None
            exc("unexpected_logic_error", e)

        # ---------- 3) desired_output_dir ----------
        desired_output_dir = None
        try:
            # path desiderato dall'utente — prendi il csv salvato in precedenza se disponibile
            desired_output_dir = None
            try:
                desired_output_dir = self.create_video_subfolder_for_csv(getattr(self, "_last_saved_colors_csv", None))
            except Exception:
                desired_output_dir = None

            # fallback: se non abbiamo un csv salvato, usa Desktop/Video
            if not desired_output_dir:
                desired_output_dir = os.path.expanduser(os.path.join("~", "Desktop", "Video"))
            try:
                os.makedirs(desired_output_dir, exist_ok=True)
            except Exception:
                pass

            if not desired_output_dir:
                desired_output_dir = os.path.expanduser(os.path.join("~", "Desktop", "Video"))
                ok(f"fallback_output_dir:{desired_output_dir}")
            os.makedirs(desired_output_dir, exist_ok=True)
            ok("ensured_output_dir_exists")
        except Exception as e:
            exc("mkdir_for_output_dir_failed", e)
            if not desired_output_dir:
                desired_output_dir = os.getcwd()

        # set output dir on widget if present
        try:
            if sc_widget and hasattr(sc_widget, "outputDirSelector"):
                try:
                    sc_widget.outputDirSelector.setCurrentPath(desired_output_dir)
                    ok("set_output_dir_on_outputDirSelector")
                except Exception as e:
                    exc("set_output_dir_failed_on_outputDirSelector", e)
            else:
                if sc_logic:
                    for meth in ("SetOutputDirectory", "setOutputDirectory", "setOutputPath", "SetOutputPath"):
                        try:
                            fn = getattr(sc_logic, meth, None)
                            if callable(fn):
                                try:
                                    fn(desired_output_dir)
                                    ok(f"sc_logic_method_{meth}_called_to_set_dir")
                                    break
                                except Exception as e:
                                    exc(f"sc_logic_call_{meth}_failed", e)
                        except Exception:
                            continue
        except Exception as e:
            exc("output_dir_setting_failed", e)

        # ---------- 4) Imposta i parametri nell'ordine richiesto ----------
        widget_set_any = False

        # (1) main view -> Red
        try:
            redNode = get_red_slice_node()
            if sc_widget and hasattr(sc_widget, "viewNodeSelector") and redNode:
                try:
                    sc_widget.viewNodeSelector.setCurrentNode(redNode)
                    ok("main_view_set_to_Red")
                    widget_set_any = True
                    # aggiorna opzioni
                    try:
                        sc_widget.updateViewOptions()
                    except Exception:
                        pass
                except Exception as e:
                    exc("set_main_view_failed", e)
            else:
                fail("no_viewNodeSelector_or_no_Red_slice_node_found")
        except Exception as e:
            exc("main_view_setting_failed", e)

        # (2) capture mode -> SLICE_SWEEP
        try:
            if sc_widget and hasattr(sc_widget, "animationModeWidget"):
                if setComboBoxByItemData(sc_widget.animationModeWidget, "SLICE_SWEEP") or setComboBoxByItemData(sc_widget.animationModeWidget, "slice sweep"):
                    ok("capture_mode_set_to_Slice_sweep")
                    widget_set_any = True
                    try:
                        sc_widget.updateViewOptions()
                    except Exception:
                        pass
                else:
                    fail("could_not_set_capture_mode_to_Slice_sweep")
            else:
                fail("no_animationModeWidget_found_on_sc_widget")
        except Exception as e:
            exc("capture_mode_setting_failed", e)

        # (3) output type -> VIDEO
        try:
            if sc_widget and hasattr(sc_widget, "outputTypeWidget"):
                if setComboBoxByItemData(sc_widget.outputTypeWidget, "VIDEO") or setComboBoxByItemData(sc_widget.outputTypeWidget, "video"):
                    ok("output_type_set_to_Video")
                    widget_set_any = True
                    try:
                        sc_widget.updateOutputType()
                    except Exception:
                        pass
                else:
                    fail("could_not_set_output_type_to_Video")
            else:
                fail("no_outputTypeWidget_found_on_sc_widget")
        except Exception as e:
            exc("output_type_setting_failed", e)

        # (4) number of images -> 220
        try:
            if sc_widget and hasattr(sc_widget, "numberOfStepsSliderWidget"):
                try:
                    sc_widget.numberOfStepsSliderWidget.value = 220
                    # trigger logic that depends on numberOfSteps
                    if hasattr(sc_widget, "setNumberOfSteps"):
                        try:
                            sc_widget.setNumberOfSteps(220)
                        except Exception:
                            pass
                    ok("number_of_images_set_to_220")
                    widget_set_any = True
                except Exception as e:
                    exc("set_number_of_images_failed", e)
            else:
                fail("no_numberOfStepsSliderWidget_found_on_sc_widget")
        except Exception as e:
            exc("number_of_images_section_failed", e)

        # (5) output file name -> axial.mp4 (videoFileNameWidget)
        try:
            if sc_widget and hasattr(sc_widget, "videoFileNameWidget"):
                try:
                    sc_widget.videoFileNameWidget.text = "axial.mp4"
                    ok("video_output_file_name_set_to_axial_mp4")
                    widget_set_any = True
                except Exception as e:
                    exc("set_video_file_name_failed", e)
            else:
                fail("no_videoFileNameWidget_found_on_sc_widget")
        except Exception as e:
            exc("video_file_name_section_failed", e)

        # (6) video length -> 10s
        try:
            if sc_widget and hasattr(sc_widget, "videoLengthSliderWidget"):
                try:
                    sc_widget.videoLengthSliderWidget.value = 10.0
                    # call setter to update dependent frame rate
                    try:
                        sc_widget.setVideoLength(10.0)
                    except Exception:
                        try:
                            sc_widget.setVideoLength()
                        except Exception:
                            pass
                    ok("video_length_set_to_10s")
                    widget_set_any = True
                except Exception as e:
                    exc("set_video_length_failed", e)
            else:
                fail("no_videoLengthSliderWidget_found_on_sc_widget")
        except Exception as e:
            exc("video_length_section_failed", e)

        # se la logic offre metodi, prova a impostare in logica (best-effort)
        try:
            if sc_logic:
                try:
                    if hasattr(sc_logic, "setOutputDirectory"):
                        try:
                            sc_logic.setOutputDirectory(desired_output_dir)
                            ok("sc_logic.setOutputDirectory_called")
                        except Exception as e:
                            exc("sc_logic_setOutputDirectory_failed", e)
                    # set number/length se disponibili
                    if hasattr(sc_logic, "SetNumberOfImages"):
                        try:
                            sc_logic.SetNumberOfImages(220)
                        except Exception:
                            pass
                    if hasattr(sc_logic, "SetVideoLength"):
                        try:
                            sc_logic.SetVideoLength(10)
                        except Exception:
                            pass
                except Exception as e:
                    exc("sc_logic_attempts_failed", e)
        except Exception as e:
            exc("sc_logic_section_failed", e)

        if not widget_set_any:
            fail("no_widget_or_logic_accepted_the_parameters")

        # popup sintetico
        try:
            msg = f"ScreenCapture setup: {len(results['successes'])} successi, {len(results['failures'])} fallimenti, {len(results['exceptions'])} eccezioni.\nOutput dir: {desired_output_dir}\nPremere 'Capture' manualmente per registrare."
            slicer.util.delayDisplay(msg, 2500)
            print("[SC][SUMMARY]", msg)
        except Exception:
            pass

        results["desired_output_dir"] = desired_output_dir
        results["sc_widget"] = sc_widget
        results["sc_logic"] = sc_logic
        return results



    def add_and_close(self, segmentEditorWidget, segmentationNode, segmentNameA, segmentNameB, closingKernelMm=5.0):
        # ensure widget / nodes are set (assumo tu abbia già fatto setSegmentationNode e setSourceVolumeNode)
        segmentEditorNode = segmentEditorWidget.mrmlSegmentEditorNode()

        # trova gli id dei segmenti a partire dal nome
        segIdA = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentNameA)
        segIdB = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentNameB)

        if not segIdA:
            raise ValueError(f"Segmento '{segmentNameA}' non trovato nella segmentation node.")
        if not segIdB:
            raise ValueError(f"Segmento '{segmentNameB}' non trovato nella segmentation node.")

        # --- 1) Imposta segmento target (quello che verrà 'addato') ---
        segmentEditorNode.SetSelectedSegmentID(segIdA)
        slicer.app.processEvents()

        # --- 2) Logical operators: UNION/ADD (fallback su ADD se UNION non funzionasse) ---
        segmentEditorWidget.setActiveEffectByName("Logical operators")
        effect = segmentEditorWidget.activeEffect()
        # imposta il modifier (il segmento che viene aggiunto al selezionato)
        effect.setParameter("ModifierSegmentID", segIdB)

        # proviamo prima con l'etichetta moderna 'UNION' (è quella documentata), altrimenti 'ADD'
        triedOps = ["UNION", "ADD", "COPY"]
        applied = False
        lastException = None
        for op in triedOps:
            try:
                effect.setParameter("Operation", op)
                slicer.app.processEvents()
                effect.self().onApply()  # esegue l'operazione
                applied = True
                break
            except Exception as e:
                lastException = e
                # prova il prossimo nome di operazione
        if not applied:
            # se nessuna op ha funzionato, rilancia l'ultima eccezione per debug
            raise RuntimeError("Logical operators apply failed.") from lastException

        slicer.app.processEvents()

        # --- 3) Rimuovi il secondo segmento (quello usato come modifier) ---
        # ATTENZIONE: rimuovere il segmento elimina ogni sua rappresentazione; assicurati che sia quello che vuoi
        segmentationNode.GetSegmentation().RemoveSegment(segIdB)
        slicer.app.processEvents()

        # --- 4) Applica smoothing: morphological closing con kernel specificato (es. 5 mm) ---
        # assicurati che sia ancora selezionato il segmento A
        segmentEditorNode.SetSelectedSegmentID(segIdA)
        slicer.app.processEvents()

        segmentEditorWidget.setActiveEffectByName("Smoothing")
        effect = segmentEditorWidget.activeEffect()
        # i nomi dei parametri e dei valori sono quelli usati dall'effetto Smoothing
        effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_CLOSING")  # metodo di closing
        # KernelSizeMm spesso accetta stringhe, per sicurezza forniamo una stringa
        effect.setParameter("KernelSizeMm", str(closingKernelMm))
        slicer.app.processEvents()

        effect.self().onApply()
        slicer.app.processEvents()

        # fine: pulizia (se usi un nodo di parameter, valuta se rimuoverlo)
        return segIdA  # opzionale: ritorna l'id del segmento risultante


    def _find_table_widget(self):
        """
        Cerca la tabella/visualizzazione dei segmenti nella UI.
        Ritorna:
        - un oggetto qt.QTableWidget se presente (tabella custom)
        - altrimenti il qMRMLSegmentsTableView (tipico widget 'segmentsTableView')
        """
        possible_names = ["tableWidget", "segmentsTable", "segmentTable", "tableWidgetSegments", "tableSegments", "segmentsTableView", "segmentsTable"]

        # 1) prima prova sul widget Qt principale caricato
        ui_container = getattr(self, "uiWidget", None)
        if ui_container is not None:
            try:
                for name in possible_names:
                    table = ui_container.findChild(qt.QTableWidget, name)
                    if table:
                        return table
                # fallback: ritorna il primo QTableWidget figlio
                for child in ui_container.children():
                    if isinstance(child, qt.QTableWidget):
                        return child
                # fallback 2: se c'è un qMRMLSegmentsTableView con objectName noto, trova quello (findChild con base QWidget)
                for name in possible_names:
                    widget = ui_container.findChild(qt.QWidget, name)
                    if widget and widget.__class__.__name__.startswith("qMRML"):
                        return widget
            except Exception:
                pass

        # 2) poi prova il namespace self.ui (childWidgetVariables)
        ui_ns = getattr(self, "ui", None)
        if ui_ns is not None:
            for name in possible_names:
                widget = getattr(ui_ns, name, None)
                if widget:
                    return widget

        return None


    def get_selected_segment_names_from_table(self):
        """
        Ritorna una lista di nomi di segmenti presi dalla tabella/segments view.
        Supporta sia QTableWidget (se usi una tabella custom) sia qMRMLSegmentsTableView.
        """
        table = self._find_table_widget()
        if not table:
            slicer.util.warningDisplay("Tabella dei segmenti non trovata nella UI.", windowTitle="Errore")
            return []

        # ---- caso qMRMLSegmentsTableView (Slicer) ----
        # qMRMLSegmentsTableView espone selectedSegmentIDs()
        if hasattr(table, "selectedSegmentIDs"):
            try:
                ids = table.selectedSegmentIDs()  # può essere QStringList oppure lista Python
            except Exception:
                # some versions might expose it with camelCase selectedSegmentIDs()
                try:
                    ids = table.selectedSegmentIDs()
                except Exception:
                    ids = []
            names = []
            # ottieni il nodo segmentation associato alla view (se presente)
            segmentationNode = None
            try:
                # qMRMLSegmentsTableView spesso fornisce segmentationNode() oppure .segmentationNode
                if hasattr(table, "segmentationNode"):
                    segmentationNode = table.segmentationNode()
                elif hasattr(table, "segmentationNode()"):
                    segmentationNode = table.segmentationNode()
            except Exception:
                segmentationNode = None

            if segmentationNode is None:
                # fallback: prendi il segmentationNode dal modulo se impostato nel widget
                segmentationNode = getattr(self, "segmentationNode", None)

            if ids:
                # ids potrebbe essere una stringa semicolon-separated in alcuni casi; normalizziamo
                if isinstance(ids, str):
                    ids = [i for i in ids.split(";") if i]
                for segId in ids:
                    try:
                        seg = segmentationNode.GetSegmentation().GetSegment(segId)
                        names.append(seg.GetName())
                    except Exception:
                        # ignora i segId che non trovi
                        continue
            return names

        # ---- caso QTableWidget custom ----
        if isinstance(table, qt.QTableWidget):
            selected_items = table.selectedItems()
            if selected_items:
                rows = sorted({item.row() for item in selected_items})
                names = []
                for r in rows:
                    item = table.item(r, 0) or table.item(r, table.columnCount() - 1)
                    if item and item.text().strip():
                        names.append(item.text().strip())
                return names

            # se non ci sono selezioni, guarda checkbox nella colonna 0
            names = []
            for r in range(table.rowCount()):
                widget = table.cellWidget(r, 0)
                if widget and isinstance(widget, qt.QCheckBox) and widget.isChecked():
                    item = table.item(r, 1) or table.item(r, 0)
                    if item and item.text().strip():
                        names.append(item.text().strip())
            return names

        # default: non sappiamo gestirlo
        return []


    def _debug_table_signals(self, table):
        # utility per debuggare quali segnali/metodi relativi alla selezione sono disponibili
        try:
            attrs = dir(table)
            interesting = [a for a in attrs if any(k in a.lower() for k in ("select", "segment", "changed", "selected"))]
            print("DEBUG: table type:", type(table), "interesting attrs/signals:", interesting)
        except Exception as e:
            print("DEBUG: cannot introspect table:", e)

    def setup_table_selection_callbacks(self):
        """
        Collega in modo robusto la selezione della tabella alla popolazione delle lineEdit.
        Supporta QTableWidget e i widget MRML (qMRMLSegmentsTableView / qMRMLSegmentsTable).
        """
        table = self._find_table_widget()
        if table is None:
            print("setup_table_selection_callbacks: nessuna tabella trovata (skip).")
            return

        # stampa debug utili (rimuovi dopo)
        self._debug_table_signals(table)

        # 1) QTableWidget: usa itemSelectionChanged
        if isinstance(table, qt.QTableWidget):
            try:
                table.itemSelectionChanged.connect(self.populate_lineedits_from_table_selection)
                print("setup_table_selection_callbacks: connesso itemSelectionChanged (QTableWidget).")
                return
            except Exception as e:
                print("setup_table_selection_callbacks: non è stato possibile connettere itemSelectionChanged:", e)

        # 2) qMRMLSegmentsTableView (o widget MRML simile): vari segnali possibili
        # Proviamo a collegare il segnale più probabile tra quelli esposti:
        # - selectionChanged(selected, deselected)
        # - segmentSelectionChanged()
        # - selectedSegmentIDsChanged()  (in alcune versioni)
        connected = False

        # helper che normalizza la chiamata alla funzione di popolamento
        def _call_populate(*args, **kwargs):
            try:
                self.populate_lineedits_from_table_selection()
            except Exception as e:
                print("Errore in populate_lineedits_from_table_selection:", e)

        # tenta diversi nomi di segnale/metodi in ordine di probabilità
        possible_signals = [
            "selectionChanged",            # Qt-style for many views
            "segmentSelectionChanged",     # qMRML specific
            "selectedSegmentIDsChanged",   # alternative naming
            "selectionModel",              # not a signal but can be used to get model
        ]

        for sig in possible_signals:
            if hasattr(table, sig):
                try:
                    attr = getattr(table, sig)
                    # se l'attributo è un segnale (callable connect) colleghiamolo,
                    # altrimenti proviamo a collegare un wrapper sulla selectionModel se è presente
                    if hasattr(attr, "connect"):
                        attr.connect(_call_populate)
                        print(f"setup_table_selection_callbacks: connesso segnale '{sig}'.")
                        connected = True
                        break
                except Exception as e:
                    # continua a provare altre opzioni
                    print(f"setup_table_selection_callbacks: imprevisto collegando '{sig}': {e}")
                    continue

        # fallback: se esiste metodo selectedSegmentIDs e non abbiamo segnale, colleghiamo un timer (last resort)
        if (not connected) and hasattr(table, "selectedSegmentIDs"):
            try:
                # tentiamo di connettere selectionChanged del selectionModel (se esiste)
                selModel = None
                if hasattr(table, "selectionModel") and callable(getattr(table, "selectionModel")):
                    try:
                        selModel = table.selectionModel()
                    except Exception:
                        selModel = None
                if selModel and hasattr(selModel, "selectionChanged"):
                    selModel.selectionChanged.connect(lambda s, d: _call_populate())
                    connected = True
                    print("setup_table_selection_callbacks: connesso selectionModel.selectionChanged (fallback).")
                else:
                    # se tutto il resto fallisce, logghiamo un warning ma non crashiamo
                    print("setup_table_selection_callbacks: non trovato segnale di selezione; l'aggiornamento manuale rimane possibile.")
            except Exception as e:
                print("setup_table_selection_callbacks: fallback failed:", e)

        if not connected:
            print("setup_table_selection_callbacks: nessun segnale disponibile collegato (non critico).")

    def populate_lineedits_from_table_selection(self):
        names = self.get_selected_segment_names_from_table()
        if not names:
            # non è un errore grave: semplicemente non c'è selezione
            return

        # trova i QLineEdit corretti (adatta i nomi se li hai diversi)
        lineA = getattr(self.ui, "lineEdit", None)
        lineB = getattr(self.ui, "lineEdit_5", None) or getattr(self.ui, "lineEdit2", None) or getattr(self.ui, "lineEdit_1", None)

        if lineA and hasattr(lineA, "setText"):
            lineA.setText(names[0])
        if len(names) > 1 and lineB and hasattr(lineB, "setText"):
            lineB.setText(names[1])


    def perform_add_from_selected_table(self):
        names = self.get_selected_segment_names_from_table()
        if len(names) < 2:
            slicer.util.warningDisplay("Seleziona almeno due segmenti nella tabella (prima -> target, seconda -> modifier).", windowTitle="Errore")
            return

        segA_name = names[0]
        segB_name = names[1]

        # prova a usare il segmentationNode attualmente gestito dal modulo
        segmentationNode = getattr(self, "segmentationNode", None)
        if segmentationNode is None:
            segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
        if segmentationNode is None:
            slicer.util.warningDisplay("Nessuna segmentation node trovata per eseguire l'operazione.", windowTitle="Errore")
            return

        try:
            self.add_and_close(
                segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor,
                segmentationNode = segmentationNode,
                segmentNameA = segA_name,
                segmentNameB = segB_name,
                closingKernelMm = 5.0
            )
            slicer.util.infoDisplay(f"Union di '{segB_name}' su '{segA_name}' completata.", windowTitle="OK")
        except Exception as e:
            slicer.util.errorDisplay(f"Errore durante l'operazione: {str(e)}")

    def perform_subtract_from_selected_table(self):
        """
        Legge i primi due segmenti selezionati nella view dei segmenti e applica
        Logical operators -> SUBTRACT (target = primo, modifier = secondo).
        Non elimina nulla né applica smoothing.
        """
        table = self._find_table_widget()
        if table is None:
            slicer.util.errorDisplay("Tabella dei segmenti non trovata nella UI.", windowTitle="Errore")
            return

        # legge selectedSegmentIDs (può essere lista Python o stringa separata da ;)
        try:
            selectedIDs = table.selectedSegmentIDs()
        except Exception as e:
            slicer.util.errorDisplay(f"Impossibile leggere la selezione dalla table: {e}", windowTitle="Errore")
            return

        if not selectedIDs:
            slicer.util.warningDisplay("Seleziona due segmenti nella tabella (primo = target, secondo = modifier).", windowTitle="Info")
            return

        # normalizza in lista
        if isinstance(selectedIDs, str):
            selectedIDs = [i for i in selectedIDs.split(";") if i]

        if len(selectedIDs) < 2:
            slicer.util.warningDisplay("Seleziona due segmenti (prima il target, poi il modifier).", windowTitle="Info")
            return

        segIdA = selectedIDs[0]
        segIdB = selectedIDs[1]

        # ottieni il segmentationNode dalla view (fallback alla variabile del modulo o alla prima segmentation nella scena)
        try:
            segmentationNode = table.segmentationNode()
        except Exception:
            segmentationNode = getattr(self, "segmentationNode", None)
        if segmentationNode is None:
            segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
        if segmentationNode is None:
            slicer.util.errorDisplay("Nessuna segmentation node disponibile.", windowTitle="Errore")
            return

        # prepara il Segment Editor widget
        try:
            segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        except Exception as e:
            slicer.util.errorDisplay(f"Impossibile ottenere il Segment Editor widget: {e}", windowTitle="Errore")
            return

        # assicura che il widget punti al segmentation node giusto
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setSegmentationNode(segmentationNode)
        # opzionale: imposta source volume se vuoi (commentato)
        # masterVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        # segmentEditorWidget.setSourceVolumeNode(masterVolumeNode)

        # imposta il segmento target come selezionato nel SegmentEditorNode
        segmentEditorNode = segmentEditorWidget.mrmlSegmentEditorNode()
        segmentEditorNode.SetSelectedSegmentID(segIdA)
        slicer.app.processEvents()

        # attiva l'effetto Logical operators e imposta il modifier
        segmentEditorWidget.setActiveEffectByName("Logical operators")
        effect = segmentEditorWidget.activeEffect()
        if effect is None:
            slicer.util.errorDisplay("Impossibile attivare l'effetto 'Logical operators'.", windowTitle="Errore")
            return

        effect.setParameter("ModifierSegmentID", segIdB)

        # prova ad applicare l'operazione SUBTRACT con fallback su nomi alternativi
        triedOps = ["SUBTRACT", "DIFFERENCE", "REMOVE"]
        applied = False
        lastException = None
        for op in triedOps:
            try:
                effect.setParameter("Operation", op)
                slicer.app.processEvents()
                # esegui l'apply
                effect.self().onApply()
                applied = True
                break
            except Exception as e:
                lastException = e
                # prova il prossimo nome di operazione

        if not applied:
            # mostra errore dettagliato
            msg = "Logical operators apply failed."
            if lastException:
                msg += f" Ultima eccezione: {lastException}"
            slicer.util.errorDisplay(msg, windowTitle="Errore")
            return

        slicer.app.processEvents()
        slicer.util.infoDisplay(f"Subtract: '{segIdB}' sottratto da '{segIdA}'.", windowTitle="OK")
        # non cancelliamo nulla e non facciamo smoothing
        return True

    def apply_threshold_strictly_inside_copy(self, segmentationNode, copySegId, minThreshold, maxThreshold):
        """
        Assicura (per quanto possibile) che Threshold venga applicata solo dentro copySegId.
        Se fallisce, ritorna False.
        """
        
        import time, logging
        try:
            segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        except Exception as e:
            logging.error("No segment editor widget: " + str(e))
            return False
        segEdNode = segmentEditorWidget.mrmlSegmentEditorNode()
        if segEdNode is None:
            return False

         # assicura che il widget punti alla segmentation giusta
        try:
            segmentEditorWidget.setSegmentationNode(segmentationNode)
        except Exception:
            pass
        slicer.app.processEvents()
        time.sleep(0.02)
        slicer.app.processEvents()

         # Forza selezione della copia
        try:
            segmentEditorWidget.setCurrentSegmentID(copySegId)
        except Exception:
            pass
        try:
            segEdNode.SetSelectedSegmentID(copySegId)
        except Exception:
            pass
        slicer.app.processEvents()
        time.sleep(0.03)
        slicer.app.processEvents()

        # imposta source/master volume (preferisci Source API)
        masterVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        if masterVolumeNode:
            if hasattr(segEdNode, 'SetAndObserveSourceVolumeNode'):
                try:
                    segEdNode.SetAndObserveSourceVolumeNode(masterVolumeNode)
                    segmentEditorWidget.setSourceVolumeNode(masterVolumeNode)
                except Exception:
                    pass
            else:
                try:
                    segEdNode.SetAndObserveMasterVolumeNode(masterVolumeNode)
                    segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)
                except Exception:
                    pass
        # Assicura widget punti alla segmentation giusta
        try:
            segmentEditorWidget.SetAndObserveSegmentationNode(segmentationNode)
        except Exception:
            pass
        slicer.app.processEvents()
        time.sleep(0.03)
        slicer.app.processEvents()

       

        # maskInside / maskEverywhere: cerca in vtkMRMLSegmentationNode, poi fallback sull'istanza segEdNode
        try:
            maskInside = slicer.vtkMRMLSegmentationNode.EditAllowedInsideVisibleSegments
            maskEverywhere = slicer.vtkMRMLSegmentationNode.EditAllowedEverywhere
        except Exception:
            # fallback: valori comunemente usati (non ideale ma resiliente)
            maskEverywhere = 0
            maskInside = 2

        try:
            overwriteNone = segEdNode.OverwriteNone
        except Exception:
            overwriteNone = 2

        # Applica mask inside + overwrite none
        try:
            segEdNode.SetMaskMode(maskInside)
            # setta il segmento di mask (se richiesto da alcune build)
            try:
                segEdNode.SetMaskSegmentID(copySegId)
            except Exception:
                pass
            segEdNode.SetOverwriteMode(overwriteNone)
        except Exception as e:
            logging.warning("apply_threshold: non posso impostare mask/overwrite: %s" % e)


        # Set overwrite to allow overlap (do not destroy others)
        try:
            segEdNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
        except Exception:
            segEdNode.SetOverwriteMode(2)

        # Apply threshold effect
        try:
            segmentEditorWidget.setActiveEffectByName('Threshold')
            effect = segmentEditorWidget.activeEffect()
            if effect is None:
                return False
            effect.setParameter('MinimumThreshold', str(minThreshold))
            effect.setParameter('MaximumThreshold', str(maxThreshold))
            slicer.app.processEvents()
            effect.self().onApply()
            slicer.app.processEvents()
        except Exception as e:
            print("Error applying threshold via SegmentEditor:", e)
            return False

        # Ripristina masking Everywhere (caller deciderà quale OverwriteMode usare)
        segEdNode.SetMaskMode(maskEverywhere)
        segEdNode.SetMaskSegmentID(None)
        
        slicer.app.processEvents()
        return True


    def split_selected_segment_inplace_using_threshold_helper(self, minThreshold=500, maxThreshold=100000):
        """
        Flusso che:
        - duplica segmento selezionato
        - rende visibile solo la copia
        - legge minThreshold da self.ui.lineEdit_8 (fallback al parametro minThreshold)
        - chiama apply_threshold_strictly_inside_copy(...) sulla copia
        - esegue Islands, Grow from seeds, Smoothing
        - cancella la copia di lavoro e ripristina visibilità
        """
        try:
            names = self.get_selected_segment_names_from_table()
            if not names:
                slicer.util.warningDisplay("Seleziona un segmento nella tabella.", windowTitle="Errore")
                return False
            selected_name = names[0]

            segmentationNode = getattr(self, "segmentationNode", None)
            if segmentationNode is None:
                segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if segmentationNode is None:
                slicer.util.errorDisplay("Nessuna segmentation node trovata.", windowTitle="Errore")
                return False
            segmentation = segmentationNode.GetSegmentation()

            # trova source id
            sourceSegId = segmentation.GetSegmentIdBySegmentName(str(selected_name))
            if not sourceSegId:
                slicer.util.errorDisplay(f"Segmento '{selected_name}' non trovato.", windowTitle="Errore")
                return False

            # salva visibilità e nascondi tutti
            displayNode = segmentationNode.GetDisplayNode()
            originalVisibility = {}
            for i in range(segmentation.GetNumberOfSegments()):
                segId = segmentation.GetNthSegmentID(i)
                originalVisibility[segId] = bool(displayNode.GetSegmentVisibility(segId))
                displayNode.SetSegmentVisibility(segId, False)
            slicer.app.processEvents()

            # duplica in-place
            before_ids = set(segmentation.GetSegmentIDs())
            segmentation.CopySegmentFromSegmentation(segmentation, sourceSegId, False)
            slicer.app.processEvents()
            after_ids = set(segmentation.GetSegmentIDs())
            new_ids = list(after_ids - before_ids)
            if not new_ids:
                slicer.util.errorDisplay("Duplicazione fallita.", windowTitle="Errore")
                # restore visibilità
                for segId, wasVis in originalVisibility.items():
                    displayNode.SetSegmentVisibility(segId, wasVis)
                return False
            copySegId = new_ids[-1]
            segmentation.GetSegment(copySegId).SetName(segmentation.GetSegment(sourceSegId).GetName() + "_copy")
            slicer.app.processEvents()

            # rendi visibile solo la copia (originale nascosto)
            for segId in list(originalVisibility.keys()):
                displayNode.SetSegmentVisibility(segId, False)
            displayNode.SetSegmentVisibility(copySegId, True)
            displayNode.SetSegmentVisibility(sourceSegId, False)
            slicer.app.processEvents()

            # ----------------------------
            # Leggi il valore della soglia da UI: lineEdit_8
            # parsing robusto: chiama .text(), strip(), converti a float con fallback
            ui_min_threshold = self.ui.lineEdit_8.text
            if not ui_min_threshold.strip(): 
                ui_min_threshold = "500"
            # ----------------------------

            # CHIAMA L'HELPER THRESHOLD (usa il valore letto da UI)
            ok = self.apply_threshold_strictly_inside_copy(segmentationNode, copySegId,
                                                        minThreshold=ui_min_threshold,
                                                        maxThreshold=maxThreshold)
            if not ok:
                slicer.util.warningDisplay("Masking/Threshold non applicabile: eseguo fallback (no-op).")
                # ripristina visibilità e esci
                for segId, wasVis in originalVisibility.items():
                    displayNode.SetSegmentVisibility(segId, wasVis)
                return False

            # usa il Segment Editor UI per gli effetti successivi (Islands, Grow, Smoothing)
            segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
            segmentEditorWidget.setSegmentationNode(segmentationNode)

            # ISLANDS: split islands to segments
            voxelsize = self.ui.lineEdit_5.text
            if not voxelsize.strip(): 
                voxelsize = "50"

            segmentEditorWidget.setActiveEffectByName('Islands')
            islandsEffect = segmentEditorWidget.activeEffect()
            if islandsEffect:
                # imposta param MinimumSize in modo robusto (cerca param che contengono 'size' o 'minimum')
                try:
                    paramNames = list(islandsEffect.parameterNames())
                except Exception:
                    paramNames = ['MinimumSize', 'Size', 'minimumsize']
                for pname in paramNames:
                    if 'size' in pname.lower():
                        try:
                            islandsEffect.setParameter(pname, str(int(voxelsize)))
                        except Exception:
                            pass
                try:
                    islandsEffect.setParameter('Operation', 'SPLIT_ISLANDS_TO_SEGMENTS')
                except Exception:
                    pass
                slicer.app.processEvents()
                try:
                    islandsEffect.self().onApply()
                except Exception:
                    try:
                        islandsEffect.self().onApply()
                    except Exception:
                        pass
                slicer.app.processEvents()

            # GROW FROM SEEDS
            segmentEditorWidget.setActiveEffectByName('Grow from seeds')
            growEffect = segmentEditorWidget.activeEffect()
            if growEffect:
                try:
                    if hasattr(growEffect, 'parameterNames') and 'SeedLocalityFactor' in list(growEffect.parameterNames()):
                        growEffect.setParameter('SeedLocalityFactor', str(8))
                except Exception:
                    pass
                slicer.app.processEvents()
                try:
                    growEffect.self().onPreview()
                except Exception:
                    pass
                try:
                    growEffect.self().onApply()
                except Exception:
                    pass
                slicer.app.processEvents()

            # SMOOTHING GAUSSIAN 0.5 mm sui nuovi segmenti (escludi la copia)
            all_ids_after = set(segmentation.GetSegmentIDs())
            created_after_dup = all_ids_after - before_ids
            if sourceSegId in created_after_dup:
                created_after_dup.discard(sourceSegId)
            segmentEditorWidget.setActiveEffectByName('Smoothing')
            smoothEffect = segmentEditorWidget.activeEffect()
            if smoothEffect:
                try:
                    smoothEffect.setParameter('SmoothingMethod', 'GAUSSIAN')
                    smoothEffect.setParameter('GaussianStandardDeviationMm', str(0.5))
                except Exception:
                    pass
                slicer.app.processEvents()
                for segId in sorted(created_after_dup):
                    try:
                        if segId == copySegId:
                            continue
                        segmentEditorWidget.setCurrentSegmentID(segId)
                        slicer.app.processEvents()
                        smoothEffect.self().onApply()
                    except Exception:
                        pass
                    slicer.app.processEvents()

            # rimuovi la copia di lavoro
            try:
                if segmentation.GetSegment(copySegId):
                    segmentationNode.RemoveSegment(copySegId)
            except Exception:
                pass
            slicer.app.processEvents()

            # ripristina visibilità originale e rendi visibili i nuovi pezzi
            for segId, wasVis in originalVisibility.items():
                displayNode.SetSegmentVisibility(segId, wasVis)
            all_ids_final = set(segmentation.GetSegmentIDs())
            new_created_final = all_ids_final - set(originalVisibility.keys())
            for segId in new_created_final:
                try:
                    displayNode.SetSegmentVisibility(segId, True)
                except Exception:
                    pass
            slicer.app.processEvents()

            # update UI
            self.onSegmentationNodeChanged(segmentationNode)
            slicer.util.infoDisplay("Split in-place completed.", windowTitle="OK")
            return True

        except Exception as e:
            import traceback, logging
            logging.error(traceback.format_exc())
            slicer.util.errorDisplay("Errore nella split: " + str(e))
            # restore vis se possibile
            try:
                if 'originalVisibility' in locals():
                    for segId, wasVis in originalVisibility.items():
                        displayNode.SetSegmentVisibility(segId, wasVis)
            except Exception:
                pass
            return False



    def get_selected_segment_ids_from_table(self):
        """
        Ritorna una lista di segmentIDs selezionati nella view (qMRMLSegmentsTableView)
        o, se la UI usa QTableWidget, converte i nomi in IDs.
        """
        table = self._find_table_widget()
        if table is None:
            slicer.util.errorDisplay("Tabella dei segmenti non trovata.", windowTitle="Errore")
            return []

        # caso qMRMLSegmentsTableView
        try:
            if hasattr(table, "selectedSegmentIDs"):
                ids = table.selectedSegmentIDs()
                if isinstance(ids, str):
                    ids = [i for i in ids.split(";") if i]
                return list(ids)
        except Exception:
            pass

        # caso QTableWidget custom -> ottieni nomi e converti in IDs
        try:
            if isinstance(table, qt.QTableWidget):
                selected_items = table.selectedItems()
                rows = sorted({item.row() for item in selected_items}) if selected_items else []
                names = []
                for r in rows:
                    item = table.item(r, 0) or table.item(r, table.columnCount()-1)
                    if item and item.text().strip():
                        names.append(item.text().strip())
                # converti nomi -> ids
                segmentationNode = getattr(self, "segmentationNode", None) or slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
                ids = []
                if segmentationNode:
                    seg = segmentationNode.GetSegmentation()
                    for n in names:
                        segId = seg.GetSegmentIdBySegmentName(n)
                        if segId:
                            ids.append(segId)
                return ids
        except Exception:
            pass

        return []
 

    def delete_selected_segment(self):
        """
        Elimina definitivamente il primo segmento selezionato.
        Restituisce True se successo, False altrimenti.
        """
        try:
            segIDs = self.get_selected_segment_ids_from_table()
            if not segIDs:
                slicer.util.warningDisplay("Seleziona almeno un segmento nella tabella.", windowTitle="Info")
                return False

            segId = segIDs[0]
            segmentationNode = getattr(self, "segmentationNode", None) or slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if segmentationNode is None:
                slicer.util.errorDisplay("Nessuna segmentation node disponibile.", windowTitle="Errore")
                return False

            segmentation = segmentationNode.GetSegmentation()
            seg = segmentation.GetSegment(segId)
            if seg is None:
                slicer.util.errorDisplay("Segmento non trovato.", windowTitle="Errore")
                return False

            originalName = seg.GetName()

            # Prova a rimuovere il segmento usando l'API del nodo di segmentation (fallback a segmentation.RemoveSegment)
            removed = False
            try:
                # questo è spesso il metodo disponibile
                segmentationNode.RemoveSegment(segId)
                removed = True
            except Exception:
                try:
                    segmentation.RemoveSegment(segId)
                    removed = True
                except Exception as e:
                    slicer.util.errorDisplay(f"Impossibile rimuovere il segmento: {e}", windowTitle="Errore")
                    return False

            slicer.app.processEvents()

            if removed:
                slicer.util.infoDisplay(f"Segmento '{originalName}' eliminato definitivamente.", windowTitle="OK")
                # aggiorna UI / osservatori
                try:
                    self.onSegmentationNodeChanged(segmentationNode)
                except Exception:
                    # onSegmentationNodeChanged potrebbe aspettarsi un segNode valido; se fallisce, proviamo almeno ad aggiornare la view
                    try:
                        if hasattr(self.ui, "segmentsTableView"):
                            self.ui.segmentsTableView.setSegmentationNode(segmentationNode)
                    except Exception:
                        pass
                return True

            return False

        except Exception as e:
            slicer.util.errorDisplay("Errore nella cancellazione: " + str(e))
            return False


    def onSegmentationNodeChanged(self, segNode): 
        #remove unused observers
        if hasattr(self, '_obsTags'): 
            for obj, evt, tag in self._obsTags: 
                obj.RemoveObserver(tag) 
        self._obsTags = [] 
        self.segmentationNode = segNode 

        #connect the view
        self.ui.segmentsTableView.setMRMLScene(slicer.mrmlScene) 
        self.ui.segmentsTableView.setSegmentationNode(segNode) 

        #observer on the MRML node 
        nodeEvent = slicer.vtkMRMLSegmentationNode.SegmentationChangedEvent 
        tag = segNode.AddObserver(nodeEvent, self._onSegmentationObjectReplaced) 
        self._obsTags.append((segNode, nodeEvent, tag)) 

        #observer on single elements
        segmentation = segNode.GetSegmentation() 
        for eventName in ('SegmentAdded', 'SegmentRemoved', 'SegmentModified'): 
            eventId = getattr(slicer.vtkSegmentation, eventName) 
            tag = segmentation.AddObserver(eventId, self.onSegmentChanged) 
            self._obsTags.append((segmentation, eventId, tag)) 

    def _onSegmentationObjectReplaced(self, caller, event): 
        '''Recalls _init to connect the observers to the new vtkSegmentation.'''
        self._initializeSegmentTableSync(self.segmentationNode) 

    def onSegmentChanged(self, caller, event): 
        '''Called every time a segment is modified.'''
        #self.ui.segmentsTableView.updateWidgetFromMRML() 

    def exportSegmentationAndOpenInBlender(
        segmentationNode=None,
        segmentIDs=None,
        outputFolder=r"C:\Users\JetsLab\Desktop\TESI MAIA ZAPPIA\STL Model",
        blenderExecutablePath=r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        fileFormat='STL',
        showInBackground=False
    ):
        """
        Export segmentation segments as STL files and open them in Blender.

        Parameters
        - segmentationNode: vtkMRMLSegmentationNode instance OR the node name (string),
                        OR a widget object that exposes the segmentation node (e.g. segmentEditorWidget),
                        OR None (uses first segmentation in scene).
        - segmentIDs: None (export all) or list of segmentID strings or segment names
        - outputFolder: destination folder (if None, asks the user via dialog)
        - blenderExecutablePath: path to blender executable
        - fileFormat: 'STL' (default) or 'OBJ' (STL recommended for addon-free import)
        - showInBackground: if True start Blender with --background (no UI)
        Returns True on success, False on error.
        """
        import os
        import subprocess
        import json
        import slicer
        import vtk
        from qt import QFileDialog

        # --- resolve segmentationNode robustly (accept node, name, widget, None) ---
        def _resolve_seg_node(obj):
            # None -> first segmentation in scene
            if obj is None:
                return slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            # string -> try to get node by name or id
            if isinstance(obj, str):
                try:
                    return slicer.util.getNode(obj)
                except Exception:
                    return None
            # already a VTK node?
            if hasattr(obj, "IsA") and obj.IsA("vtkMRMLSegmentationNode"):
                return obj
            # widget-like object: try segmentationNode() or segmentationNode attr or getSegmentationNode()
            try:
                if hasattr(obj, "segmentationNode") and callable(getattr(obj, "segmentationNode")):
                    candidate = obj.segmentationNode()
                    if candidate and hasattr(candidate, "IsA") and candidate.IsA("vtkMRMLSegmentationNode"):
                        return candidate
                if hasattr(obj, "segmentationNode") and not callable(getattr(obj, "segmentationNode")):
                    candidate = getattr(obj, "segmentationNode")
                    if candidate and hasattr(candidate, "IsA") and candidate.IsA("vtkMRMLSegmentationNode"):
                        return candidate
                if hasattr(obj, "getSegmentationNode") and callable(getattr(obj, "getSegmentationNode")):
                    candidate = obj.getSegmentationNode()
                    if candidate and hasattr(candidate, "IsA") and candidate.IsA("vtkMRMLSegmentationNode"):
                        return candidate
            except Exception:
                pass
            return None

        # Resolve node
        segmentationNode = _resolve_seg_node(segmentationNode)
        if segmentationNode is None:
            segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
        if segmentationNode is None or not (hasattr(segmentationNode, "IsA") and segmentationNode.IsA("vtkMRMLSegmentationNode")):
            slicer.util.errorDisplay("Nessun nodo di segmentazione valido trovato nella scena. Seleziona un nodo di segmentazione.")
            return False

        # If outputFolder not provided, ask user via dialog
        if not outputFolder:
            outputFolder = QFileDialog.getExistingDirectory(None, "Seleziona cartella per esportazione")
            if not outputFolder:
                slicer.util.errorDisplay("Nessuna cartella selezionata. Operazione annullata.")
                return False
        os.makedirs(outputFolder, exist_ok=True)
        import tempfile, time

        # crea una sottocartella unica per questa esecuzione
        safe_name_for_folder = "export"  # o ricava dal nome del segmentationNode se vuoi
        unique_folder = os.path.join(outputFolder, f"{safe_name_for_folder}_{int(time.time())}")
        os.makedirs(unique_folder, exist_ok=True)
        outputFolder = unique_folder  # reindirizzi le esportazioni qui

        # Ensure closed surface representation exists (best-effort)
        try:
            segmentationNode.CreateClosedSurfaceRepresentation()
        except Exception:
            # ignore but continue; Export function will create if needed
            pass

        # Prepare vtkStringArray of segment IDs if requested, otherwise collect all
        vtkIDs = None
        if segmentIDs:
            # user provided list: convert names -> IDs if needed
            seg = segmentationNode.GetSegmentation()
            vtkIDs = vtk.vtkStringArray()
            for sid in segmentIDs:
                if isinstance(sid, str):
                    # If it's a name, try convert to ID; if not found assume already an ID string
                    segId = seg.GetSegmentIdBySegmentName(sid)
                    if segId:
                        vtkIDs.InsertNextValue(segId)
                    else:
                        vtkIDs.InsertNextValue(str(sid))
                else:
                    vtkIDs.InsertNextValue(str(sid))
        else:
            # collect all segment IDs from the segmentation
            seg = segmentationNode.GetSegmentation()
            n = seg.GetNumberOfSegments()
            vtkIDs = vtk.vtkStringArray()
            # GetSegmentIDs API differs across versions; use GetSegmentIDs if available, else iterate
            try:
                idsTemp = vtk.vtkStringArray()
                seg.GetSegmentIDs(idsTemp)
                for i in range(idsTemp.GetNumberOfValues()):
                    vtkIDs.InsertNextValue(idsTemp.GetValue(i))
            except Exception:
                for i in range(seg.GetNumberOfSegments()):
                    vtkIDs.InsertNextValue(seg.GetNthSegmentID(i))

        # Export segments using Segmentations logic
        logic = slicer.modules.segmentations.logic()
        success = logic.ExportSegmentsClosedSurfaceRepresentationToFiles(
            outputFolder,
            segmentationNode,
            vtkIDs,
            fileFormat.upper(),
            True,   # use LPS coords
            1.0,    # size scale
            False   # merge multiple segments?
        )
        if not success:
            slicer.util.errorDisplay("Esportazione fallita. Controlla la segmentation / reference volume.")
            return False

        # Collect exported files
        exported_files = []
        ext = '.stl' if fileFormat.upper() == 'STL' else '.obj'
        for f in os.listdir(outputFolder):
            if f.lower().endswith(ext):
                exported_files.append(os.path.join(outputFolder, f))

        if not exported_files:
            slicer.util.errorDisplay("Nessun file esportato trovato nella cartella: " + outputFolder)
            return False

        # Create Blender import script (STL import is native)
        folderName = segmentationNode.GetSegmentation().GetSegment(segmentationNode.GetSegmentation().GetNthSegmentID(0)).GetName()
        folderName = re.sub(r'\s*\d+$', '', folderName)

        script_lines = [
        "import bpy, os, struct, mathutils, traceback",
        f'folder = r\"{outputFolder}\"',
        f'folderName = {json.dumps(folderName)}',
        "",
        "# ---------- CONFIG ----------",
        "VOXEL_SIZE = 0.2        # riduci per più dettaglio (es. 0.3)",
        "DECIMATE_RATIO = 0.5    # rapporto di decimazione richiesto",
        "APPLY_TRANSFORMS = True",
        "# ----------------------------",
        "",
        "# --- elimina il cubo di default ---",
        "for obj in list(bpy.data.objects):",
        "    if obj.type == 'MESH' and obj.name == 'Cube':",
        "        bpy.data.objects.remove(obj, do_unlink=True)",
        "",
        "# --- funzione per leggere STL binario ---",
        "def read_stl(filepath):",
        "    vertices, faces = [], []",
        "    try:",
        "        with open(filepath, 'rb') as f:",
        "            f.read(80)",
        "            num_triangles = struct.unpack('<I', f.read(4))[0]",
        "            for i in range(num_triangles):",
        "                f.read(12)  # normal",
        "                v1 = struct.unpack('<3f', f.read(12))",
        "                v2 = struct.unpack('<3f', f.read(12))",
        "                v3 = struct.unpack('<3f', f.read(12))",
        "                vertices.extend([v1, v2, v3])",
        "                faces.append((3*i, 3*i+1, 3*i+2))",
        "                f.read(2)",
        "    except Exception as e:",
        "        print(f'Errore leggendo {filepath}: {e}')",
        "    return vertices, faces",
        "",
        "# --- funzione custom per esportare OBJ senza addon ---",
        "def export_obj(obj, filepath):",
        "    try:",
        "        mesh = obj.data",
        "        verts = [obj.matrix_world @ v.co for v in mesh.vertices]",
        "        faces = [tuple(p.vertices) for p in mesh.polygons]",
        "        with open(filepath, 'w', encoding='utf-8') as f:",
        "            f.write(f'o {obj.name}\\n')",
        "            for v in verts:",
        "                f.write(f'v {v.x} {v.y} {v.z}\\n')",
        "            for face in faces:",
        "                indices = [str(i+1) for i in face]",
        "                f.write('f ' + ' '.join(indices) + '\\n')",
        "    except Exception as e:",
        "        print(f'Errore esportando OBJ {filepath}: {e}')",
        "",
        "# --- vettore di shift per posizionare i frammenti nella posizione desiderata ---",
        "shift_vector = mathutils.Vector((-138.2302, 71.851, 0))",
        "",
        "# --- importa e dispone gli STL sovrapposti al centro ---",
        "imported_objs = []",
        "for fn in os.listdir(folder):",
        "    if fn.lower().endswith('.stl'):",
        "        path = os.path.join(folder, fn)",
        "        verts, faces = read_stl(path)",
        "        if verts and faces:",
        "            mesh = bpy.data.meshes.new(fn)",
        "            try:",
        "                mesh.from_pydata(verts, [], faces)",
        "                mesh.update()",
        "            except Exception as e:",
        "                print(f'Errore creando mesh da {fn}:', e)",
        "                continue",
        "            obj = bpy.data.objects.new(fn, mesh)",
        "            obj.location = (0, 0, 0)  # tutti sovrapposti al centro",
        "            bpy.context.collection.objects.link(obj)",
        "            imported_objs.append(obj)",
        "",
        "            # --- scala e centra origine sull'oggetto appena importato ---",
        "            obj.scale = (0.1, 0.1, 0.1)",
        "            bpy.context.view_layer.objects.active = obj",
        "            obj.select_set(True)",
        "            try:",
        "                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')",
        "            except Exception:",
        "                pass",
        "            obj.select_set(False)",
        "",
        "            # --- applica shift per posizionare il frammento nella posizione desiderata ---",
        "            obj.location += shift_vector",
        "",
        "# --- centra la vista sugli oggetti importati ---",
        "for obj_sel in imported_objs:",
        "    obj_sel.select_set(True)",
        "try:",
        "    bpy.ops.view3d.view_selected(use_all_regions=False)",
        "except Exception:",
        "    pass",
        "for obj_sel in imported_objs:",
        "    obj_sel.select_set(False)",
        "",
        "# --- prepara e processa ogni oggetto singolarmente: clean -> remesh -> decimate -> triangulate -> normals ---",
        "if not imported_objs:",
        "    print('Nessun oggetto importato dalla cartella:', folder)",
        "else:",
        "    for obj in imported_objs:",
        "        try:",
        "            bpy.context.view_layer.objects.active = obj",
        "            obj.select_set(True)",
        "",
        "            # APPLY TRANSFORMS (location/rotation/scale) per sicurezza",
        "            if APPLY_TRANSFORMS:",
        "                try:",
        "                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)",
        "                except Exception as e:",
        "                    print('transform_apply failed for', obj.name, e)",
        "",
        "            # Clean geometry: merge by distance + recalc normals",
        "            try:",
        "                if bpy.context.mode != 'OBJECT':",
        "                    bpy.ops.object.mode_set(mode='OBJECT')",
        "                bpy.ops.object.mode_set(mode='EDIT')",
        "                bpy.ops.mesh.select_all(action='SELECT')",
        "                try:",
        "                    bpy.ops.mesh.merge_by_distance()",
        "                except Exception:",
        "                    # older blender versions fallback",
        "                    try:",
        "                        bpy.ops.mesh.remove_doubles()",
        "                    except Exception as ee:",
        "                        print('merge/remove_doubles failed for', obj.name, ee)",
        "                try:",
        "                    bpy.ops.mesh.normals_make_consistent(inside=False)",
        "                except Exception as ee:",
        "                    print('normals fix failed for', obj.name, ee)",
        "                bpy.ops.object.mode_set(mode='OBJECT')",
        "            except Exception as e:",
        "                print('Clean geometry failed for', obj.name, e)",
        "",
        "            # REMESH (Voxel) to get watertight geometry",
        "            try:",
        "                rem = obj.modifiers.new(name='RemeshVoxel', type='REMESH')",
        "                rem.mode = 'VOXEL'",
        "                rem.voxel_size = VOXEL_SIZE",
        "                # apply remesh",
        "                bpy.ops.object.modifier_apply(modifier=rem.name)",
        "            except Exception as e:",
        "                print('Remesh failed for', obj.name, e)",
        "",
        "            # DECIMATE (collapse)",
        "            try:",
        "                dec = obj.modifiers.new(name='Decimate', type='DECIMATE')",
        "                dec.ratio = DECIMATE_RATIO",
        "                if hasattr(dec, 'use_preserve_volume'):",
        "                    dec.use_preserve_volume = True",
        "                bpy.ops.object.modifier_apply(modifier=dec.name)",
        "            except Exception as e:",
        "                print('Decimate failed for', obj.name, e)",
        "",
        "            # TRIANGULATE",
        "            try:",
        "                tri = obj.modifiers.new(name='Triangulate', type='TRIANGULATE')",
        "                bpy.ops.object.modifier_apply(modifier=tri.name)",
        "            except Exception as e:",
        "                print('Triangulate failed for', obj.name, e)",
        "",
        "            # Final normals and small cleanup",
        "            try:",
        "                bpy.ops.object.mode_set(mode='EDIT')",
        "                bpy.ops.mesh.select_all(action='SELECT')",
        "                bpy.ops.mesh.normals_make_consistent(inside=False)",
        "                bpy.ops.object.mode_set(mode='OBJECT')",
        "            except Exception as e:",
        "                print('Final normals recalc failed for', obj.name, e)",
        "",
        "            obj.select_set(False)",
        "            print('Processed:', obj.name)",
        "        except Exception as exc:",
        "            print('Unexpected error processing', obj.name, traceback.format_exc())",
        "",
        "unity_roots = [r'C:\\\\Users\\\\JetsLab\\\\Desktop\\\\TESI MAIA ZAPPIA\\\\UnityApp\\\\Fracture Reduction SB\\\\Assets\\\\Resources\\\\', r'C:\\\\Users\\\\JetsLab\\\\Desktop\\\\TESI MAIA ZAPPIA\\\\UnityApp\\\\Fracture Reduction VR\\\\Assets\\\\Resources\\\\']",
        "",
        "for unity_root in unity_roots:",
        "    unity_folder = os.path.join(unity_root, folderName)",
        "    os.makedirs(unity_folder, exist_ok=True)",
        "    for obj in imported_objs:",
        "        try:",
        "            safe_name = obj.name if not obj.name.lower().endswith('.obj') else obj.name[:-4]",
        "            export_path = os.path.join(unity_folder, safe_name + '.obj')",
        "            export_obj(obj, export_path)",
        "        except Exception as e:",
        "            print('Errore esportando', obj.name, e)",
        "",
        "print('IMPORT_AND_EXPORT_TO_UNITY_OK')"
        ]





        script_content = "\n".join(script_lines) + "\n"
        script_file = os.path.join(outputFolder, "blender_import_script.py")
        try:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception as e:
            slicer.util.errorDisplay("Impossibile scrivere lo script per Blender: " + str(e))
            return False

        # Launch Blender with the script
        def find_blender(provided_path=None):
            import shutil
            # 1) explicit provided path
            if provided_path and os.path.isfile(provided_path):
                return provided_path
            # 2) PATH
            path_from_which = shutil.which("blender")
            if path_from_which:
                return path_from_which
            # 3) common Windows locations
            common_paths = [
                r"C:\Program Files\Blender Foundation\Blender\blender.exe",
                r"C:\Program Files\Blender Foundation\blender.exe",
                r"C:\Program Files\Blender\blender.exe",
                r"C:\Program Files (x86)\Blender Foundation\Blender\blender.exe",
            ]
            for p in common_paths:
                if os.path.isfile(p):
                    return p
            return None

        blender_exe = find_blender(blenderExecutablePath)
        if blender_exe is None:
            msg = ("Blender non è stato trovato automaticamente.\n\n"
                f"I file esportati sono in: {outputFolder}\n\n"
                "Puoi aprirli manualmente in Blender (File → Import → STL),\n"
                "oppure specifica il percorso di blender.exe passando blenderExecutablePath.")
            slicer.util.confirmOkCancelDisplay(msg, windowTitle="Export finished (but Blender not found)")
            return True

        cmd = [blender_exe]
        if showInBackground:
            cmd += ["--background"]
        cmd += ["--python", script_file]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            slicer.util.errorDisplay("Impossibile lanciare Blender: " + str(e) + "\nI file sono in: " + outputFolder)
            return False

        slicer.util.infoDisplay("Esportazione completata. File: {}\nBlender avviato.".format(", ".join(exported_files)))
        return True
                    
    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.inputVolume = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[FracturedBoneSegmentationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputVolume and self._parameterNode.thresholdedVolume:
            self.ui.applyButton.toolTip = _("Compute output volume")
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select input and output volume nodes")
            self.ui.applyButton.enabled = False

    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            # Compute output
            self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode(),
                               self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)

            # Compute inverted output (if needed)
            if self.ui.invertedOutputSelector.currentNode():
                # If additional output volume is selected then result with inverted threshold is written there
                self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
                                   self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)


#
# FracturedBoneSegmentationLogic
#


class FracturedBoneSegmentationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return FracturedBoneSegmentationParameterNode(super().getParameterNode())

    def process(self,
                inputVolume: vtkMRMLScalarVolumeNode,
                outputVolume: vtkMRMLScalarVolumeNode,
                imageThreshold: float,
                invert: bool = False,
                showResult: bool = True) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info("Processing started")

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            "InputVolume": inputVolume.GetID(),
            "OutputVolume": outputVolume.GetID(),
            "ThresholdValue": imageThreshold,
            "ThresholdType": "Above" if invert else "Below",
        }
        cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
        # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")


#
# FracturedBoneSegmentationTest
#


class FracturedBoneSegmentationTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_FracturedBoneSegmentation1()

    def test_FracturedBoneSegmentation1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("FracturedBoneSegmentation1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = FracturedBoneSegmentationLogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
