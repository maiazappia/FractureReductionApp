cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(FractureReductionApp)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/FractureReductionApp")
set(EXTENSION_CONTRIBUTORS "Maia Zappia (UNIGE)")
set(EXTENSION_DESCRIPTION "Tool for automatic segmentation of fractured bones.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/FractureReductionApp.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/FractureReductionApp/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(DataLoad)
add_subdirectory(Segmentation)
add_subdirectory(FractureSegmentation)
add_subdirectory(FracturedBoneSegmentation)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
