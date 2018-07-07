# Open a Windows CMD shell and give:
#
#    "C:\Program Files\Slicer 4.9.0-2018-06-20\Slicer.exe"  --python-script loadrotatesave.py  -i "E:/ILENIA_BAGLIVO/DCMData/"  -o "E:/ILENIA_BAGLIVO/3D_SLICER"
#
#    needs 4.9 because of imageNode.HardenTransform() 
#
# Other options to remember: --no-main-window
# Options -i and -o can also be --input-folder and --output-folder respectively

# WORK IN PROGRESS!!
# WORK IN PROGRESS!!
# WORK IN PROGRESS!!

import argparse, sys, shutil, os, logging
import vtk, qt, ctk, slicer
import DICOMLib
from DICOMLib import DICOMUtils
#from DICOMLib.DICOMUtils import TemporaryDICOMDatabase

# Inspired by
# https://github.com/SlicerRt/SlicerRT/tree/master/BatchProcessing
# https://github.com/SlicerProstate/mpReview/blob/master/mpReviewPreprocessor.py
# https://github.com/SlicerRt/SegmentRegistration/blob/master/ProstateMRIUSContourPropagation/ProstateMRIUSContourPropagation.py for DICOM export
# These links are also interesting
# https://gist.github.com/pieper/6186477
# https://stackoverflow.com/questions/5137497/find-current-directory-and-files-directory
# Basics
# https://discourse.slicer.org/t/start-programming-in-slicer-transforms-module-elastix/2499

# In the code, two variables can be set:
#
# var: chooses one of two different approaches with vTransform (but they seem equivalent); to be investigated
# doResample: resamples or not, but they seem equivalent!
#
# I had four different series saved:
#
# var = True, doResample = False -> ScalarVolume_7 (I renamed it 7a)
# var = False, doResample = False -> ScalarVolume_7  (I renamed it 7b)
# var = True, doResample = True -> ScalarVolume_10
# var = False, doResample = True -> ScalarVolume_11

def main(argv):
  print('STARTING!')
  try:
    parser = argparse.ArgumentParser(description="to be done")
    parser.add_argument("-i", "--input-folder", dest="input_folder", metavar="PATH",
                        default="-", required=True, help="Folder of input DICOM files (can contain sub-folders)")
    parser.add_argument("-o", "--output-folder", dest="output_folder", metavar="PATH",
                        default=".", help="Folder to save converted datasets")
    args = parser.parse_args(argv)

    if args.input_folder == "-":
      print('Please specify input DICOM study folder!')
    if args.output_folder == ".":
      print('Current directory is selected as output folder (default). To change it, please specify --output-folder')

    # Convert to python path style
    args.input_folder = args.input_folder.replace('\\', '/')
    args.output_folder = args.output_folder.replace('\\', '/')

    logging.info("Importing DICOM data from " + args.input_folder)
    DICOMUtils.openTemporaryDatabase()
    DICOMUtils.importDicom(args.input_folder)
    logging.info("Loading first patient into Slicer")
    patient = slicer.dicomDatabase.patients()[0]
    DICOMUtils.loadPatientByUID(patient)
    #logging.info(patient) # it is just a string containing the id number
	
    # APPLY TRANSFORMS, THEN SAVE	
    #
    node_key = 'vtkMRMLScalarVolumeNode*'
    sv_nodes = slicer.util.getNodes(node_key)
    
    for imageNode in sv_nodes.values():        # imageNode is the current image node; in fact, sv_nodes.values()[0] is the only image so I could say: imageNode = sv_nodes.values()[0]
 	
	      # https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository  look for "transform = slicer.vtkMRMLLinearTransformNode()"
        # http://apidocs.slicer.org/master/classvtkMRMLVolumeNode.html  for ApplyTransform() and ApplyTransformMatrix()
	
	      #   t = vtk.vtkMatrix4x4()
	      #   t.setElement(0,0,1)
		
        # Apply transform   https://www.vtk.org/doc/nightly/html/classvtkTransform.html   (Scale, Translate, RotateX, ...)
        logging.info("Applying transform")

        # Two ways, they seem equivalent, to be better understood
        var = False
        if var:
            vTransform = vtk.vtkTransform()
            vTransform.Translate(-0.88, 35.4, 5.65)  # translate by -isocenter
            vTransform.RotateZ(10)  # The angle is in degrees
            vTransform.Translate(0.88, -35.4, -5.65)
            imageNode.ApplyTransform(vTransform)
        else:
            transform = slicer.vtkMRMLLinearTransformNode()
            scene = slicer.mrmlScene
            scene.AddNode(transform) 
            imageNode.SetAndObserveTransformNodeID(transform.GetID())
            vTransform = vtk.vtkTransform()
            vTransform.Translate(-0.88, 35.4, 5.65)  # translate by -isocenter
            vTransform.RotateZ(10)  # The angle is in degrees
            vTransform.Translate(0.88, -35.4, -5.65)
            transform.SetAndObserveMatrixTransformToParent(vTransform.GetMatrix())
            #transform.SetMatrixTransformToParent(vTransform.GetMatrix())	
	          
	      # harden transform
        # https://www.slicer.org/wiki/Documentation/Nightly/Developers/Python_scripting
        #logic = slicer.vtkSlicerTransformLogic()
        #logic.hardenTransform(imageNode)

        imageNode.HardenTransform() 

        # Resample (https://github.com/SlicerRt/SegmentRegistration/blob/master/ProstateMRIUSContourPropagation/ProstateMRIUSContourPropagation.py line 725)
        #           https://www.slicer.org/wiki/Documentation/4.8/Modules/ResampleScalarVolume
        doResample = True
        if doResample:
            logging.info("Resampling")
            #
            # Create output volume
            resampledImageNode = slicer.vtkMRMLScalarVolumeNode()
            resampledImageNode.SetName('Resampled')
            slicer.mrmlScene.AddNode(resampledImageNode)
            # Resample
            resampleParameters = {'outputPixelSpacing':'0,0,0', 'interpolationType':'lanczos', 'InputVolume':imageNode, 'OutputVolume':resampledImageNode.GetID()}
            slicer.cli.run(slicer.modules.resamplescalarvolume, None, resampleParameters, wait_for_completion=True)

	      ## Save all of the ScalarVolumes (or whatever is in node_key) to NRRD files
	      ##     (commented out)
        ##  logging.info("Save image volumes nodes to directory %s: %s" % (args.output_folder, ','.join(sv_nodes.keys())))
        #	
        ## Clean up file name and set path
        #fileName = imageNode.GetName() + '.nrrd'
        #charsToRemove = ['!', '?', ':', ';']
        #fileName = fileName.translate(None, ''.join(charsToRemove))
        #fileName = fileName.replace(' ', '_')
        #filePath = args.output_folder + '/' + fileName
        #logging.info('  Saving image ' + imageNode.GetName() + '\n    to file <' + filePath + '>')
        #
        # Save to file
        #success = slicer.util.saveNode(imageNode, filePath)
        #if not success:
        #  logging.error('Failed to save image volume: ' + filePath)

        # DICOM
        #
        logging.info("Saving as DICOM series")
        # http://apidocs.slicer.org/master/classvtkMRMLSubjectHierarchyNode.html
        # shNode is a vtkMRMLSubjectHierarchyNode
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        # get the id of the first (and only) node in the node hierarchy, which is the patient
        # parent is shNode.GetSceneItemID()
        patientID = shNode.GetItemByPositionUnderParent (shNode.GetSceneItemID(), 0)
        # now get the id of the study
        studyID = shNode.GetItemByPositionUnderParent (patientID, 0)

        # https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Export_a_volume_to_DICOM_file_format

        if doResample:
            volumeID = shNode.GetItemByPositionUnderParent (studyID, 1)    # resampled
        else:
            volumeID = shNode.GetItemByPositionUnderParent (studyID, 0)   # original
                    
        #patientItemID = shNode.CreateSubjectItem(shNode.GetSceneItemID(), "Test patient")
        #studyItemID = shNode.CreateStudyItem(patientItemID, "Test study")
        #shNode.SetItemParent(volumeID, studyItemID)

        import DICOMScalarVolumePlugin
        exporter = DICOMScalarVolumePlugin.DICOMScalarVolumePluginClass()
        exportables = exporter.examineForExport(volumeID)
        for exp in exportables:
            exp.directory = args.output_folder
        exporter.export(exportables)

     #   slicer.mrmlScene.Clear(0)

  except Exception, e:
    print e
#  sys.exit()
  return

if __name__ == "__main__":
  main(sys.argv[1:])


# Some interesting stuff/links/etc

# https://github.com/SlicerRt/SegmentRegistration/blob/master/ProstateMRIUSContourPropagation/ProstateMRIUSContourPropagation.py
# there are also the calculation of DICE and HAUSDORFF

#   slicer.mrmlScene.Clear(0)   #  clear the scene

## Choose first patient from the patient list
#      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
#      patient = slicer.dicomDatabase.patients()[0]
#      studies = slicer.dicomDatabase.studiesForPatient(patient)
#      series = [slicer.dicomDatabase.seriesForStudy(study) for study in studies]
#      seriesUIDs = [uid for uidList in series for uid in uidList]
#      dicomWidget.detailsPopup.offerLoadables(seriesUIDs, 'SeriesUIDList')
#      dicomWidget.detailsPopup.examineForLoading()
      
    # imageNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)   #??? does it work?



        # Open DICOM export dialog, selecting the study to export
     #   exportDicomDialog = slicer.qSlicerDICOMExportDialog(None)
     #   exportDicomDialog.setMRMLScene(slicer.mrmlScene)
     #   exportDicomDialog.execDialog(studyID)
      
     #input_folder = 'F:/ILENIA_BAGLIVO/DCMData/'
     # outputFolder = "E:/ILENIA_BAGLIVO/3D_SLICER/OUT"

#    [success, dsa] = slicer.util.loadVolume(r'C:/Program Files/Slicer 4.8.1/share/Slicer-4.8/qt-loadable-modules/EMSegment/Tasks/MRI-Human-Brain/atlas_t2.nrrd', returnNode=True)
